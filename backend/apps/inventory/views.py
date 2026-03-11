from rest_framework import viewsets, status
from common.logging import trace
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.db.models import Count
from apps.accounts.permissions import (
    ReadOnlyForViewers, IsOperatorOrAbove, IsAdmin, IsAgentOrOperatorOrAbove
)
from common.agent_auth import AgentAPIKeyAuthentication
from .models import Device, DeviceGroup
from .filters import DeviceFilter
from .serializers import (
    DeviceGroupSerializer, DeviceGroupCreateSerializer,
    DeviceListSerializer, DeviceDetailSerializer, DeviceCreateSerializer,
    DeviceBulkTagSerializer
)
from common.pagination import StandardPageNumberPagination
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.patches.models import DevicePatchStatus
from apps.patches.serializers import DevicePatchStatusSerializer

# Auth classes used for agent-accessible endpoints
_AGENT_AUTH = [AgentAPIKeyAuthentication, JWTAuthentication]


class DeviceViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyForViewers]
    filterset_class = DeviceFilter
    search_fields = ["hostname", "ip_address", "tags"]
    ordering_fields = ["hostname", "last_seen", "status", "os_family", "created_at"]

    def get_queryset(self):
        return Device.objects.exclude(status=Device.Status.DECOMMISSIONED).order_by('hostname')

    def get_serializer_class(self):
        if self.action == 'list':
            return DeviceListSerializer
        elif self.action in ['update', 'partial_update']:
            return DeviceCreateSerializer
        return DeviceDetailSerializer

    def create(self, request, *args, **kwargs):
        """Override create to return full device detail (including api_key) on 201."""
        serializer = DeviceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = serializer.save()
        out = DeviceDetailSerializer(device, context={'request': request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    # ------------------------------------------------------------------ #
    # Read-only actions                                                    #
    # ------------------------------------------------------------------ #

    @extend_schema(summary="Get device compliance", description="Detailed compliance breakdown for a single device.")
    @action(detail=True, methods=["get"])
    def compliance(self, request, pk=None):
        device = self.get_object()
        serializer = DeviceDetailSerializer(device)
        return Response(serializer.get_compliance_summary(device))

    @extend_schema(summary="List patches", description="List all DevicePatchStatus for this device. Filter by ?state=missing,installed,failed,pending. Sort by ?ordering=-last_attempt for recent.")
    @action(detail=True, methods=["get"], pagination_class=StandardPageNumberPagination)
    def patches(self, request, pk=None):
        device = self.get_object()
        statuses = DevicePatchStatus.objects.filter(device=device).select_related('patch').order_by('patch__vendor_id')
        state_filter = request.query_params.get('state')
        if state_filter:
            states = [s.strip() for s in state_filter.split(',')]
            statuses = statuses.filter(state__in=states)
        ordering = request.query_params.get('ordering')
        if ordering:
            allowed = {'last_attempt', '-last_attempt', 'installed_at', '-installed_at', 'patch__severity', '-patch__severity'}
            if ordering in allowed:
                statuses = statuses.order_by(ordering)
        page = self.paginate_queryset(statuses)
        if page is not None:
            serializer = DevicePatchStatusSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DevicePatchStatusSerializer(statuses, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Installed applications", description="Return installed apps from device inventory data.")
    @action(detail=True, methods=["get"])
    def installed_apps(self, request, pk=None):
        device = self.get_object()
        apps = device.inventory_data.get('apps', []) if device.inventory_data else []
        search = request.query_params.get('search', '').lower()
        if search:
            apps = [a for a in apps if search in (a.get('name', '') or '').lower() or search in (a.get('publisher', '') or '').lower()]
        return Response({'count': len(apps), 'results': apps})

    @extend_schema(summary="System info summary", description="Return aggregated system info from device metadata and inventory.")
    @action(detail=True, methods=["get"], url_path="system_info")
    def system_info(self, request, pk=None):
        device = self.get_object()
        meta = device.metadata or {}
        inv = device.inventory_data or {}
        return Response({
            'hostname': device.hostname,
            'ip_address': device.ip_address,
            'mac_address': device.mac_address,
            'os_family': device.os_family,
            'os_name': getattr(device, 'os_name', '') or device.os_family,
            'os_version': device.os_version,
            'os_arch': device.os_arch,
            'agent_version': device.agent_version,
            'environment': device.environment,
            'status': device.status,
            'last_seen': device.last_seen,
            'created_at': device.created_at,
            'serial_number': meta.get('serial_number', ''),
            'cpu_count': meta.get('cpu_count'),
            'cpu_model': meta.get('cpu_model', ''),
            'total_ram': meta.get('total_ram'),
            'total_disk': meta.get('total_disk'),
            'uptime': meta.get('uptime', ''),
            'cpu_usage': meta.get('cpu_usage', 0),
            'ram_usage': meta.get('ram_usage', 0),
            'disk_usage': meta.get('disk_usage', 0),
            'battery': inv.get('battery'),
            'network': inv.get('network', []),
            'storage': inv.get('storage', []),
            'last_login': inv.get('last_login'),
            'boot_time': meta.get('boot_time', ''),
            'domain': meta.get('domain', ''),
            'manufacturer': meta.get('manufacturer', ''),
            'model': meta.get('model', ''),
        })

    @extend_schema(summary="List deployments", description="List recent DeploymentTargets for this device.")
    @action(detail=True, methods=["get"])
    def deployments(self, request, pk=None):
        device = self.get_object()
        from apps.deployments.models import DeploymentTarget
        targets = DeploymentTarget.objects.filter(device=device).order_by('-started_at')[:20]
        data = [{
            "deployment_id": str(t.deployment.id),
            "deployment_name": t.deployment.name,
            "status": t.status,
            "started_at": t.started_at,
            "completed_at": t.completed_at
        } for t in targets]
        return Response(data)

    @extend_schema(summary="Bulk scan devices", description="Trigger patch scan on multiple devices.")
    @action(detail=False, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def bulk_scan(self, request):
        from .tasks import scan_device_patches
        device_ids = request.data.get("device_ids")
        
        if device_ids:
            queryset = Device.objects.filter(id__in=device_ids, status=Device.Status.ONLINE)
        else:
            queryset = Device.objects.filter(status=Device.Status.ONLINE)

        count = 0
        for device in queryset:
            scan_device_patches.delay(str(device.id))
            count += 1
            
        return Response({"status": f"Scan triggered for {count} online devices."})

    @extend_schema(summary="Device statistics", description="Aggregate measurements across fleet.")
    @action(detail=False, methods=["get"])
    def stats(self, request):
        total = Device.objects.count()
        online = Device.objects.filter(status=Device.Status.ONLINE).count()
        by_os = list(Device.objects.values('os_family').annotate(count=Count('id')))
        by_env = list(Device.objects.values('environment').annotate(count=Count('id')))
        by_status = list(Device.objects.values('status').annotate(count=Count('id')))
        return Response({
            'total': total,
            'online_count': online,
            'by_os': by_os,
            'by_environment': by_env,
            'by_status': by_status
        })

    # ------------------------------------------------------------------ #
    # Agent-accessible endpoints (API key OR JWT)                         #
    # ------------------------------------------------------------------ #

    @extend_schema(
        summary="Agent self-identify",
        description="Returns the device record for the currently authenticated agent (by X-Agent-API-Key). "
                    "Used by the realtime service as a fallback auth mechanism in dev/SQLite mode.",
    )
    @action(
        detail=False, methods=["get"],
        url_path="me",
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    def me(self, request):
        from common.agent_auth import AgentPrincipal
        if isinstance(request.user, AgentPrincipal):
            device = request.user.device
            serializer = DeviceDetailSerializer(device, context={"request": request})
            return Response(serializer.data)
        return Response({"error": "Not an agent"}, status=status.HTTP_403_FORBIDDEN)

    @extend_schema(summary="Agent Heartbeat", description="Agent POSTs this to update last_seen, status, and system metrics.")
    @action(
        detail=True, methods=["post"],
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    @trace
    def heartbeat(self, request, pk=None):
        from django.utils import timezone
        device = self.get_object()
        device.last_seen = timezone.now()
        device.status = Device.Status.ONLINE
        meta = request.data.get("payload", request.data)
        if meta:
            # Update direct fields if present
            if 'mac_address' in meta: device.mac_address = meta['mac_address']
            if 'os_arch' in meta: device.os_arch = meta['os_arch']
            if 'agent_version' in meta: device.agent_version = meta['agent_version']
            
            existing = device.metadata or {}
            # Update metadata json with all spec fields
            spec_fields = (
                "cpu_usage", "ram_usage", "disk_usage", "agent_version",
                "cpu_count", "total_ram", "total_disk", "uptime", "serial_number",
                "log_level", "heartbeat_interval"
            )
            for field in spec_fields:
                if field in meta:
                    existing[field] = meta[field]
            device.metadata = existing
        device.save(update_fields=["last_seen", "status", "metadata", "mac_address", "os_arch", "agent_version"])
        return Response({"status": "heartbeat received", "device_id": str(device.id)})

    @extend_schema(
        summary="Ingest fast-lane metrics",
        description="Persist lightweight performance metrics from fast-lane collection (every ~5s). Updates device metadata with real-time CPU/RAM/Disk/Network/IO stats.",
    )
    @action(
        detail=True, methods=["post"], url_path="ingest_metrics",
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    @trace
    def ingest_metrics(self, request, pk=None):
        from django.utils import timezone
        device = self.get_object()
        data = request.data

        device.last_seen = timezone.now()
        device.status = Device.Status.ONLINE

        existing = device.metadata or {}
        metrics_fields = (
            "cpu_percent", "cpu_per_core", "memory_percent", "memory_used_bytes",
            "memory_total_bytes", "disk_usage_percent", "disk_read_bytes_sec",
            "disk_write_bytes_sec", "net_sent_bytes_sec", "net_recv_bytes_sec",
            "process_count",
        )
        for field in metrics_fields:
            if field in data:
                existing[field] = data[field]

        # Also map to legacy field names for backward compatibility
        if "cpu_percent" in data:
            existing["cpu_usage"] = data["cpu_percent"]
        if "memory_percent" in data:
            existing["ram_usage"] = data["memory_percent"]
        if "disk_usage_percent" in data:
            existing["disk_usage"] = data["disk_usage_percent"]

        existing["last_metrics_ts"] = data.get("timestamp")
        device.metadata = existing
        device.save(update_fields=["last_seen", "status", "metadata"])

        return Response({"status": "metrics accepted", "device_id": str(device.id)})

    @extend_schema(
        summary="Ingest scan results",
        description=(
            "Called by agent (via X-Agent-API-Key) or realtime service after a scan completes. "
            "Persists patch states and updates DevicePatchStatus records asynchronously."
        ),
    )
    @action(
        detail=True, methods=["post"],
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    @trace
    def ingest_scan(self, request, pk=None):
        device = self.get_object()
        patches = request.data.get("patches", [])

        if not patches:
            return Response(
                {"status": "no patches in payload", "device_id": str(device.id)},
                status=status.HTTP_200_OK,
            )

        from .tasks import process_scan_results
        try:
            process_scan_results.delay(str(device.id), patches)
        except Exception:
            # Fallback: run synchronously if Celery broker is unavailable (dev mode)
            import logging
            logging.getLogger(__name__).warning(
                "Celery broker unavailable — running process_scan_results synchronously"
            )
            process_scan_results.apply(args=[str(device.id), patches])

        return Response(
            {
                "status": "scan results accepted",
                "device_id": str(device.id),
                "patch_count": len(patches),
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(
        summary="Ingest inventory info",
        description="Persist detailed hardware and software inventory data from agent.",
    )
    @action(
        detail=True, methods=["post"],
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    @trace
    def ingest_inventory(self, request, pk=None):
        device = self.get_object()
        inventory = request.data.get("inventory", request.data)
        if inventory:
            device.inventory_data = inventory
            device.save(update_fields=["inventory_data"])
        return Response({"status": "inventory accepted", "device_id": str(device.id)})

    @extend_schema(
        summary="Ingest health check result",
        description="Persist live resource metrics (CPU, RAM, Disk) reported by agent health checks."
    )
    @action(
        detail=True, methods=["post"],
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    @trace
    def ingest_health_check(self, request, pk=None):
        device = self.get_object()
        data = request.data
        
        # Persist to metadata for immediate access by deployment tasks
        existing = device.metadata or {}
        existing["last_health_check"] = {
            "cpu_usage": data.get("cpu_usage"),
            "ram_usage": data.get("ram_usage"),
            "disk_usage": data.get("disk_usage"),
            "status": data.get("status"),
            "timestamp": data.get("timestamp")
        }
        device.metadata = existing
        device.save(update_fields=["metadata"])
        
        return Response({"status": "health check accepted", "device_id": str(device.id)})

    @extend_schema(
        summary="Ingest slow-lane data",
        description=(
            "Persist heavy slow-lane inventory data collected by the agent every ~15 minutes. "
            "Includes installed apps, patches, missing updates, services, security config, etc."
        ),
    )
    @action(
        detail=True, methods=["post"], url_path="ingest_slow_lane",
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
    )
    @trace
    def ingest_slow_lane(self, request, pk=None):
        device = self.get_object()
        data = request.data.get("data", request.data)

        if not data:
            return Response(
                {"status": "no data in payload", "device_id": str(device.id)},
                status=status.HTTP_200_OK,
            )

        # Merge slow-lane data into inventory_data
        existing_inv = device.inventory_data or {}
        existing_inv["slow_lane"] = data
        existing_inv["slow_lane_ts"] = request.data.get("timestamp")
        existing_inv["slow_lane_collection_time"] = request.data.get("collection_time_sec")

        # Also extract key lists into top-level inventory keys for backward compatibility
        # with the installed_apps and system_info endpoints
        if "registry_apps" in data:
            # Windows: merge registry apps into inventory apps list
            apps = []
            for a in (data.get("registry_apps") or []):
                apps.append({
                    "name": a.get("DisplayName"),
                    "version": a.get("DisplayVersion"),
                    "publisher": a.get("Publisher"),
                    "install_date": a.get("InstallDate"),
                    "size_mb": a.get("Size_MB"),
                })
            existing_inv["apps"] = apps
        elif "installed_packages" in data:
            # Linux: merge installed packages into inventory apps list
            existing_inv["apps"] = data.get("installed_packages") or []
        elif "homebrew_packages" in data or "app_store_apps" in data:
            # macOS: merge homebrew + app store into inventory apps list
            apps = []
            for pkg in (data.get("homebrew_packages") or []):
                apps.append({
                    "name": pkg.get("name"),
                    "version": (pkg.get("versions") or [""])[0] if isinstance(pkg.get("versions"), list) else "",
                    "publisher": pkg.get("type", "homebrew"),
                })
            for app in (data.get("app_store_apps") or []):
                apps.append({
                    "name": app.get("name"),
                    "version": app.get("version", ""),
                    "publisher": "App Store",
                })
            existing_inv["apps"] = apps

        device.inventory_data = existing_inv
        device.save(update_fields=["inventory_data"])

        # If there are missing_updates / security_updates, trigger scan processing
        missing = data.get("missing_updates") or data.get("security_updates") or []
        if missing:
            from .tasks import process_scan_results
            # Convert missing updates format to scan-compatible format
            scan_patches = []
            for u in missing:
                if isinstance(u, dict):
                    scan_patches.append({
                        "vendor_id": u.get("KB") or u.get("package") or u.get("update", ""),
                        "title": u.get("Title") or u.get("package") or u.get("update", ""),
                        "severity": u.get("Severity", "medium"),
                        "installed": False,
                    })
            if scan_patches:
                process_scan_results.delay(str(device.id), scan_patches)

        return Response(
            {
                "status": "slow lane data accepted",
                "device_id": str(device.id),
                "sections": len(data) if isinstance(data, dict) else 0,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    # ------------------------------------------------------------------ #
    # Operator actions — send commands to agent via Redis                 #
    # ------------------------------------------------------------------ #

    @extend_schema(summary="Trigger patch scan", description="Enqueue Celery task that commands the agent to run a local patch scan.")
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def scan(self, request, pk=None):
        device = self.get_object()
        if device.status != Device.Status.ONLINE:
            return Response(
                {"error": f"Device '{device.hostname}' is {device.status}. Agent must be online to scan."},
                status=status.HTTP_409_CONFLICT,
            )
        from .tasks import scan_device_patches
        scan_device_patches.delay(str(device.id))
        return Response(
            {"status": f"Scan command enqueued for '{device.hostname}'", "device_id": str(device.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(summary="Trigger reboot", description="Publish REBOOT command to agent via Redis pub/sub.")
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def reboot(self, request, pk=None):
        device = self.get_object()
        if device.status != Device.Status.ONLINE:
            return Response(
                {"error": f"Device '{device.hostname}' is {device.status}. Agent must be online to reboot."},
                status=status.HTTP_409_CONFLICT,
            )
        from common.redis_pubsub import RedisPublisher
        RedisPublisher.publish_agent_command(
            str(device.id), "REBOOT",
            {"initiated_by": str(getattr(request.user, "username", "unknown"))}
        )
        return Response(
            {"status": f"REBOOT command sent to '{device.hostname}'", "device_id": str(device.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(summary="Update agent config", description="Publish CONFIG_UPDATE command to agent.")
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def agent_config(self, request, pk=None):
        device = self.get_object()
        if device.status != Device.Status.ONLINE:
            return Response(
                {"error": f"Device '{device.hostname}' is {device.status}. Agent must be online to update config."},
                status=status.HTTP_409_CONFLICT,
            )
        from common.redis_pubsub import RedisPublisher
        config = request.data
        
        # Persist to DB first
        existing = device.metadata or {}
        if "log_level" in config: existing["log_level"] = config["log_level"]
        if "heartbeat_interval" in config: existing["heartbeat_interval"] = config["heartbeat_interval"]
        device.metadata = existing
        device.save(update_fields=["metadata"])

        RedisPublisher.publish_agent_command(
            str(device.id), "CONFIG_UPDATE",
            {"config": config}
        )
        return Response(
            {"status": "Configuration update command sent.", "device_id": str(device.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    @extend_schema(summary="Request slow-lane inventory scan", description="Publish COLLECT_SLOW_LANE command to the agent via Redis pub/sub. The agent will immediately run a full inventory collection.")
    @action(detail=True, methods=["post"], url_path="request_slow_lane", permission_classes=[IsOperatorOrAbove])
    def request_slow_lane(self, request, pk=None):
        device = self.get_object()
        if device.status != Device.Status.ONLINE:
            return Response(
                {"error": f"Device '{device.hostname}' is {device.status}. Agent must be online to scan."},
                status=status.HTTP_409_CONFLICT,
            )
        from common.redis_pubsub import RedisPublisher
        RedisPublisher.publish_agent_command(
            str(device.id), "COLLECT_SLOW_LANE",
            {"device_id": str(device.id), "initiated_by": str(getattr(request.user, "username", "unknown"))}
        )
        return Response(
            {"status": f"Inventory scan command sent to '{device.hostname}'", "device_id": str(device.id)},
            status=status.HTTP_202_ACCEPTED,
        )

    # ------------------------------------------------------------------ #
    # Bulk operations                                                      #
    # ------------------------------------------------------------------ #

    @extend_schema(summary="Bulk tag devices", description="Bulk add/remove tags on multiple devices.", request=DeviceBulkTagSerializer)
    @action(detail=False, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def bulk_tag(self, request):
        serializer = DeviceBulkTagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_ids = serializer.validated_data['device_ids']
        tags_to_apply = serializer.validated_data['tags']
        action_type = serializer.validated_data['action']

        devices = Device.objects.filter(id__in=device_ids)
        updated = 0
        for dev in devices:
            current_tags = dev.tags or []
            if action_type == 'add':
                dev.tags = list(set(current_tags + tags_to_apply))
            else:
                dev.tags = [t for t in current_tags if t not in tags_to_apply]
            dev.save(update_fields=["tags"])
            updated += 1

        return Response({"status": f"Bulk tag '{action_type}' applied to {updated} device(s)"})

    @extend_schema(summary="Bulk assign group", description="Add multiple devices to an existing group.")
    @action(detail=False, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def bulk_group(self, request):
        device_ids = request.data.get('device_ids', [])
        group_id = request.data.get('group_id')
        if not group_id:
            return Response({"error": "group_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            group = DeviceGroup.objects.get(id=group_id)
            devices = Device.objects.filter(id__in=device_ids)
            for dev in devices:
                dev.groups.add(group)
            return Response({"status": f"Added {devices.count()} device(s) to group '{group.name}'"})
        except DeviceGroup.DoesNotExist:
            return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)

    # ------------------------------------------------------------------ #
    # Activity log                                                         #
    # ------------------------------------------------------------------ #

    @extend_schema(summary="Device activity log", description="Return recent activity for a device including heartbeats, scans, deployments, config changes.")
    @action(detail=True, methods=["get"])
    def activity(self, request, pk=None):
        device = self.get_object()
        from apps.deployments.models import DeploymentTarget
        activities = []

        # Recent deployment targets as activity
        targets = DeploymentTarget.objects.filter(device=device).order_by('-started_at')[:20]
        for t in targets:
            activities.append({
                "timestamp": t.started_at or t.completed_at,
                "event_type": f"deployment_{t.status}",
                "message": f"Deployment '{t.deployment.name}' — {t.status}",
                "source": "system"
            })

        # Last health check from metadata
        meta = device.metadata or {}
        if meta.get("last_health_check"):
            hc = meta["last_health_check"]
            activities.append({
                "timestamp": hc.get("timestamp"),
                "event_type": "health_check",
                "message": f"CPU={hc.get('cpu_usage', '?')}%, RAM={hc.get('ram_usage', '?')}%, Disk={hc.get('disk_usage', '?')}%",
                "source": "agent"
            })

        # Sort by timestamp desc
        activities.sort(key=lambda a: a.get("timestamp") or "", reverse=True)
        return Response({"results": activities[:50]})

    # ------------------------------------------------------------------ #
    # API Key Rotation                                                     #
    # ------------------------------------------------------------------ #

    @extend_schema(summary="Rotate agent API key", description="Generate a new API key for the device agent.")
    @action(detail=True, methods=["post"], permission_classes=[IsAdmin])
    def rotate_key(self, request, pk=None):
        import secrets
        device = self.get_object()
        new_key = secrets.token_urlsafe(32)
        device.agent_api_key = new_key
        device.save(update_fields=["agent_api_key"])
        return Response({
            "status": "API key rotated",
            "device_id": str(device.id),
            "new_api_key": new_key,
        })

    # ------------------------------------------------------------------ #
    # CSV Export                                                            #
    # ------------------------------------------------------------------ #

    @extend_schema(summary="Export devices CSV", description="Export all devices as CSV file.")
    @action(detail=False, methods=["get"])
    def export(self, request):
        import csv
        from django.http import HttpResponse
        devices = self.get_queryset()
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="devices.csv"'
        writer = csv.writer(response)
        writer.writerow(['Hostname', 'IP', 'OS', 'Status', 'Compliance %', 'Agent Version', 'Last Seen', 'Environment', 'Tags'])
        for d in devices:
            writer.writerow([
                d.hostname, d.ip_address, d.os_name or d.os_family,
                d.status, d.compliance_rate or 0, d.agent_version or '',
                d.last_seen, d.environment, ','.join(d.tags or [])
            ])
        return response

    # ------------------------------------------------------------------ #
    # Slow-lane section data (for device detail tabs)                     #
    # ------------------------------------------------------------------ #

    @extend_schema(
        summary="Get slow-lane section data",
        description=(
            "Return a specific section of slow-lane inventory (e.g. services, firewall, drivers, "
            "security_config, scheduled_tasks, local_users, event_log_errors, etc.)."
        ),
    )
    @action(detail=True, methods=["get"], url_path="slow_lane_section")
    def slow_lane_section(self, request, pk=None):
        device = self.get_object()
        section = request.query_params.get("section", "")
        inv = device.inventory_data or {}
        slow = inv.get("slow_lane", {})
        if section:
            data = slow.get(section, [])
            return Response({"section": section, "data": data, "device_id": str(device.id)})
        # No section specified — return all slow-lane keys and counts
        summary = {}
        for key, val in slow.items():
            if isinstance(val, list):
                summary[key] = len(val)
            elif isinstance(val, dict):
                summary[key] = len(val)
            else:
                summary[key] = 1
        return Response({
            "sections": summary,
            "slow_lane_ts": inv.get("slow_lane_ts"),
            "collection_time_sec": inv.get("slow_lane_collection_time"),
            "device_id": str(device.id),
        })

    # ------------------------------------------------------------------ #
    # Agent installer download                                             #
    # ------------------------------------------------------------------ #

    @extend_schema(
        summary="Download agent installer",
        description=(
            "Download a self-contained offline installer package for the agent. "
            "Query param ?os=windows|linux|macos. The installer includes Python "
            "dependencies and an install script. For the current device, the API key "
            "is pre-configured in the package."
        ),
        parameters=[
            OpenApiParameter("os", OpenApiTypes.STR, description="Target OS: windows, linux, or macos"),
        ],
    )
    @action(detail=True, methods=["get"], url_path="download_installer")
    def download_installer(self, request, pk=None):
        import zipfile
        import io
        import tempfile
        import subprocess
        from django.http import HttpResponse as DjangoHttpResponse
        from django.conf import settings as django_settings

        device = self.get_object()
        target_os = request.query_params.get("os", device.os_family or "linux").lower()

        if target_os not in ("windows", "linux", "macos"):
            return Response({"error": "os must be windows, linux, or macos"}, status=status.HTTP_400_BAD_REQUEST)

        # Build config.yaml for the device — use settings or derive from request
        rest_url = getattr(django_settings, 'AGENT_REST_URL', None)
        ws_url = getattr(django_settings, 'AGENT_WS_URL', None)
        if not rest_url:
            scheme = "https" if request.is_secure() else "http"
            host = request.get_host()
            rest_url = f"{scheme}://{host}/api/v1"
        if not ws_url:
            ws_scheme = "wss" if request.is_secure() else "ws"
            host = request.get_host()
            ws_url = f"{ws_scheme}://{host}/ws/agent"

        config_content = (
            f"# PatchGuard Agent Configuration — auto-generated\n"
            f"server_url: \"{ws_url}\"\n"
            f"rest_url: \"{rest_url}\"\n"
            f"api_key: \"{device.agent_api_key}\"\n"
            f"device_id_override: \"{device.id}\"\n"
            f"auto_register: false\n"
            f"heartbeat_interval: 60\n"
            f"rest_heartbeat_interval: 300\n"
            f"fast_lane_interval: 5\n"
            f"slow_lane_interval: 900\n"
            f"log_level: info\n"
            f"tags: []\n"
        )

        # Create ZIP archive of the agent bundle
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            import os as _os
            agent_dir = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(__file__))), "..", "agent")
            agent_dir = _os.path.abspath(agent_dir)
            req_file = _os.path.join(agent_dir, "requirements.txt")

            # Add core agent files
            for root, dirs, files in _os.walk(agent_dir):
                # Skip __pycache__, tests, .git
                dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", "tests")]
                for f in files:
                    if f.endswith((".pyc", ".pyo")):
                        continue
                    filepath = _os.path.join(root, f)
                    arcname = _os.path.relpath(filepath, agent_dir)
                    # Replace config.yaml with device-specific one
                    if arcname == "config.yaml":
                        zf.writestr("patchguard-agent/config.yaml", config_content)
                    else:
                        zf.write(filepath, f"patchguard-agent/{arcname}")

            # Bundle pip wheels for offline install
            if _os.path.isfile(req_file):
                try:
                    tmp_deps = tempfile.mkdtemp(prefix="pg_deps_")
                    subprocess.run(
                        ["pip", "download", "-r", req_file, "-d", tmp_deps,
                         "--no-cache-dir", "--quiet"],
                        check=True, timeout=120,
                    )
                    for whl in _os.listdir(tmp_deps):
                        whl_path = _os.path.join(tmp_deps, whl)
                        if _os.path.isfile(whl_path):
                            zf.write(whl_path, f"patchguard-agent/deps/{whl}")
                except Exception:
                    # If pip download fails, include a note but don't block
                    zf.writestr(
                        "patchguard-agent/deps/README.txt",
                        "Offline wheels could not be bundled.\n"
                        "Run: pip download -r requirements.txt -d deps/\n"
                        "Then re-run install to use offline mode.\n"
                    )
                finally:
                    import shutil
                    shutil.rmtree(tmp_deps, ignore_errors=True)

            # Add OS-specific install script
            if target_os == "windows":
                zf.writestr("patchguard-agent/install.bat", self._windows_install_script())
                zf.writestr("patchguard-agent/install.ps1", self._windows_install_ps1())
            elif target_os == "linux":
                zf.writestr("patchguard-agent/install.sh", self._linux_install_script())
            else:  # macos
                zf.writestr("patchguard-agent/install.sh", self._macos_install_script())

            # Add a README
            zf.writestr("patchguard-agent/INSTALL.md", self._installer_readme(target_os))

        buf.seek(0)
        filename = f"patchguard-agent-{target_os}-{device.hostname}.zip"
        resp = DjangoHttpResponse(buf.read(), content_type="application/zip")
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'
        return resp

    # ── Installer script generators ──────────────────────────────────────

    @staticmethod
    def _windows_install_script():
        return (
            '@echo off\n'
            'echo === PatchGuard Agent Installer (Windows) ===\n'
            'echo.\n'
            'echo [1/4] Checking Python...\n'
            'python --version >nul 2>&1 || (\n'
            '    echo ERROR: Python not found. Install Python 3.10+ and re-run.\n'
            '    pause\n'
            '    exit /b 1\n'
            ')\n'
            'echo [2/4] Creating virtual environment...\n'
            'python -m venv venv\n'
            'call venv\\Scripts\\activate.bat\n'
            'echo [3/4] Installing dependencies (offline)...\n'
            'pip install --no-index --find-links=deps -r requirements.txt 2>nul || pip install -r requirements.txt\n'
            'echo [4/4] Starting agent...\n'
            'echo To run as a service, use: nssm install PatchGuardAgent "%CD%\\venv\\Scripts\\python.exe" "%CD%\\agent.py"\n'
            'echo Starting agent manually...\n'
            'venv\\Scripts\\python agent.py\n'
            'pause\n'
        )

    @staticmethod
    def _windows_install_ps1():
        return (
            '# PatchGuard Agent Installer (Windows PowerShell)\n'
            'Write-Host "=== PatchGuard Agent Installer ===" -ForegroundColor Cyan\n'
            '\n'
            '# Check Python\n'
            'if (-not (Get-Command python -ErrorAction SilentlyContinue)) {\n'
            '    Write-Host "ERROR: Python not found. Install Python 3.10+ and re-run." -ForegroundColor Red\n'
            '    exit 1\n'
            '}\n'
            '\n'
            'Write-Host "[1/4] Creating virtual environment..."\n'
            'python -m venv venv\n'
            '.\\venv\\Scripts\\Activate.ps1\n'
            '\n'
            'Write-Host "[2/4] Installing dependencies..."\n'
            'if (Test-Path deps) {\n'
            '    Write-Host "  -> Offline deps folder found, installing from local wheels..."\n'
            '    pip install --no-index --find-links=deps -r requirements.txt -q\n'
            '} else {\n'
            '    Write-Host "  -> Installing from PyPI..."\n'
            '    pip install -r requirements.txt -q\n'
            '}\n'
            '\n'
            'Write-Host "[3/4] Registering as Windows Service..."\n'
            '$svcName = "PatchGuardAgent"\n'
            '$pythonPath = Join-Path $PWD "venv\\Scripts\\python.exe"\n'
            '$agentPath = Join-Path $PWD "agent.py"\n'
            'if (Get-Command nssm -ErrorAction SilentlyContinue) {\n'
            '    nssm install $svcName $pythonPath $agentPath\n'
            '    nssm set $svcName AppDirectory $PWD\n'
            '    nssm start $svcName\n'
            '    Write-Host "Service registered and started." -ForegroundColor Green\n'
            '} else {\n'
            '    Write-Host "nssm not found. Install nssm for Windows service support." -ForegroundColor Yellow\n'
            '    Write-Host "Running agent directly..."\n'
            '    python agent.py\n'
            '}\n'
        )

    @staticmethod
    def _linux_install_script():
        return (
            '#!/bin/bash\nset -e\n'
            'echo "=== PatchGuard Agent Installer (Linux) ==="\n'
            'INSTALL_DIR="/opt/patchguard-agent"\n'
            'LOG_DIR="/var/log/patchguard-agent"\n'
            '\n'
            'if [ "$EUID" -ne 0 ]; then echo "Run as root (sudo)."; exit 1; fi\n'
            '\n'
            'echo "[1/5] Creating directories..."\n'
            'mkdir -p "$INSTALL_DIR" "$LOG_DIR"\n'
            'cp -r . "$INSTALL_DIR/"\n'
            '\n'
            'echo "[2/5] Installing system dependencies..."\n'
            'if command -v apt-get >/dev/null; then\n'
            '    apt-get update -qq && apt-get install -y -qq python3-pip python3-venv python3-dev\n'
            'elif command -v yum >/dev/null; then\n'
            '    yum install -y -q python3-pip python3-devel\n'
            'fi\n'
            '\n'
            'echo "[3/5] Setting up Python venv..."\n'
            'python3 -m venv "$INSTALL_DIR/venv"\n'
            '"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q\n'
            'if [ -d "$INSTALL_DIR/deps" ] && [ "$(ls -A $INSTALL_DIR/deps 2>/dev/null)" ]; then\n'
            '    echo "  -> Offline deps found, installing from local wheels..."\n'
            '    "$INSTALL_DIR/venv/bin/pip" install --no-index --find-links="$INSTALL_DIR/deps" -r "$INSTALL_DIR/requirements.txt" -q\n'
            'else\n'
            '    echo "  -> Installing from PyPI..."\n'
            '    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q\n'
            'fi\n'
            '\n'
            'echo "[4/5] Registering systemd service..."\n'
            'cat <<EOF > /etc/systemd/system/patchguard-agent.service\n'
            '[Unit]\nDescription=PatchGuard Agent\nAfter=network.target\n'
            '[Service]\nType=simple\nUser=root\nWorkingDirectory=$INSTALL_DIR\n'
            'ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/agent.py\n'
            'Restart=always\nRestartSec=10\n'
            'StandardOutput=append:$LOG_DIR/agent.log\nStandardError=append:$LOG_DIR/agent.log\n'
            '[Install]\nWantedBy=multi-user.target\nEOF\n'
            '\n'
            'echo "[5/5] Starting agent..."\n'
            'systemctl daemon-reload && systemctl enable patchguard-agent && systemctl start patchguard-agent\n'
            'echo "Done! Status: $(systemctl is-active patchguard-agent)"\n'
            'echo "Logs: tail -f $LOG_DIR/agent.log"\n'
        )

    @staticmethod
    def _macos_install_script():
        return (
            '#!/bin/bash\nset -e\n'
            'echo "=== PatchGuard Agent Installer (macOS) ==="\n'
            'INSTALL_DIR="/opt/patchguard-agent"\n'
            'LOG_DIR="/var/log/patchguard-agent"\n'
            '\n'
            'if [ "$EUID" -ne 0 ]; then echo "Run as root (sudo)."; exit 1; fi\n'
            '\n'
            'echo "[1/5] Creating directories..."\n'
            'mkdir -p "$INSTALL_DIR" "$LOG_DIR"\n'
            'cp -r . "$INSTALL_DIR/"\n'
            '\n'
            'echo "[2/5] Setting up Python venv..."\n'
            'python3 -m venv "$INSTALL_DIR/venv"\n'
            '"$INSTALL_DIR/venv/bin/pip" install --upgrade pip -q\n'
            'if [ -d "$INSTALL_DIR/deps" ] && [ "$(ls -A $INSTALL_DIR/deps 2>/dev/null)" ]; then\n'
            '    echo "  -> Offline deps found, installing from local wheels..."\n'
            '    "$INSTALL_DIR/venv/bin/pip" install --no-index --find-links="$INSTALL_DIR/deps" -r "$INSTALL_DIR/requirements.txt" -q\n'
            'else\n'
            '    echo "  -> Installing from PyPI..."\n'
            '    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" -q\n'
            'fi\n'
            '\n'
            'echo "[3/5] Creating launchd plist..."\n'
            'cat <<EOF > /Library/LaunchDaemons/com.patchguard.agent.plist\n'
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            '<plist version="1.0"><dict>\n'
            '<key>Label</key><string>com.patchguard.agent</string>\n'
            '<key>ProgramArguments</key><array>\n'
            '<string>$INSTALL_DIR/venv/bin/python</string>\n'
            '<string>$INSTALL_DIR/agent.py</string>\n'
            '</array>\n'
            '<key>WorkingDirectory</key><string>$INSTALL_DIR</string>\n'
            '<key>RunAtLoad</key><true/>\n'
            '<key>KeepAlive</key><true/>\n'
            '<key>StandardOutPath</key><string>$LOG_DIR/agent.log</string>\n'
            '<key>StandardErrorPath</key><string>$LOG_DIR/agent.log</string>\n'
            '</dict></plist>\nEOF\n'
            '\n'
            'echo "[4/5] Loading service..."\n'
            'launchctl load /Library/LaunchDaemons/com.patchguard.agent.plist\n'
            '\n'
            'echo "[5/5] Done! Agent is running."\n'
            'echo "Logs: tail -f $LOG_DIR/agent.log"\n'
        )

    @staticmethod
    def _installer_readme(target_os):
        os_instructions = {
            "windows": (
                "## Windows Installation\n\n"
                "1. Extract this ZIP to a folder (e.g. C:\\PatchGuardAgent)\n"
                "2. Run `install.bat` (basic) or `install.ps1` (PowerShell, recommended)\n"
                "3. For service: install nssm (https://nssm.cc) first\n"
                "4. Offline: deps/ folder contains pre-downloaded wheels\n"
            ),
            "linux": (
                "## Linux Installation\n\n"
                "1. Extract: `unzip patchguard-agent-linux-*.zip`\n"
                "2. Run: `cd patchguard-agent && sudo bash install.sh`\n"
                "3. Check: `systemctl status patchguard-agent`\n"
                "4. Offline: deps/ folder contains pre-downloaded wheels\n"
            ),
            "macos": (
                "## macOS Installation\n\n"
                "1. Extract: `unzip patchguard-agent-macos-*.zip`\n"
                "2. Run: `cd patchguard-agent && sudo bash install.sh`\n"
                "3. Check: `launchctl list | grep patchguard`\n"
                "4. Offline: deps/ folder contains pre-downloaded wheels\n"
            ),
        }
        return (
            "# PatchGuard Agent Installer\n\n"
            "Pre-configured with your device API key.\n\n"
            f"{os_instructions.get(target_os, '')}\n"
            "## Requirements\n\n"
            "- Python 3.10+\n"
            "- No internet required if deps/ folder was bundled\n\n"
            "## Configuration\n\n"
            "Config is in `config.yaml`. API key and server URLs are pre-filled.\n"
        )


class DeviceGroupViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyForViewers]
    queryset = DeviceGroup.objects.all().order_by('name')
    search_fields = ["name"]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return DeviceGroupCreateSerializer
        return DeviceGroupSerializer

    @extend_schema(summary="List group devices", description="List devices in this group (respects dynamic rules).")
    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        group = self.get_object()
        devices = group.get_devices()
        page = self.paginate_queryset(devices)
        if page is not None:
            serializer = DeviceListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DeviceListSerializer(devices, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Group compliance", description="Compliance rate for all devices in this group.")
    @action(detail=True, methods=["get"])
    def compliance(self, request, pk=None):
        group = self.get_object()
        devices = group.get_devices()
        total = devices.count()
        if total == 0:
            return Response({"group": group.name, "compliance_rate": 0, "total": 0, "compliant": 0})
        from django.db.models import Avg
        avg = devices.aggregate(avg_comp=Avg('compliance_rate'))['avg_comp'] or 0
        compliant = devices.filter(compliance_rate__gte=90).count()
        return Response({
            "group": group.name,
            "compliance_rate": round(avg, 1),
            "total": total,
            "compliant": compliant,
            "non_compliant": total - compliant,
        })

    @extend_schema(summary="Group tree", description="Return all groups as a nested tree (root groups only).")
    @action(detail=False, methods=["get"])
    def tree(self, request):
        roots = DeviceGroup.objects.filter(parent__isnull=True).order_by('name')
        serializer = DeviceGroupSerializer(roots, many=True, context={'request': request})
        return Response(serializer.data)
