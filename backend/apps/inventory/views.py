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

    @extend_schema(summary="Device Statistics", description="Aggregate stats across entire fleet.")
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
        process_scan_results.delay(str(device.id), patches)

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
