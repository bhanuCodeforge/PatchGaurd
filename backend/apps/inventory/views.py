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

    @extend_schema(summary="List patches", description="List all DevicePatchStatus for this device.")
    @action(detail=True, methods=["get"], pagination_class=StandardPageNumberPagination)
    def patches(self, request, pk=None):
        device = self.get_object()
        statuses = DevicePatchStatus.objects.filter(device=device).select_related('patch').order_by('patch__vendor_id')
        page = self.paginate_queryset(statuses)
        if page is not None:
            serializer = DevicePatchStatusSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DevicePatchStatusSerializer(statuses, many=True)
        return Response(serializer.data)

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
