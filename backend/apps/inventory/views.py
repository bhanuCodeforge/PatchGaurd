from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from apps.accounts.permissions import ReadOnlyForViewers, IsOperatorOrAbove, IsAdmin
from .models import Device, DeviceGroup
from .filters import DeviceFilter
from .serializers import (
    DeviceGroupSerializer, DeviceGroupCreateSerializer,
    DeviceListSerializer, DeviceDetailSerializer, DeviceCreateSerializer,
    DeviceBulkTagSerializer
)
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from apps.patches.models import DevicePatchStatus
from apps.patches.serializers import DevicePatchStatusSerializer

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
        elif self.action in ['create', 'update', 'partial_update']:
            return DeviceCreateSerializer
        return DeviceDetailSerializer

    @extend_schema(summary="Get device compliance", description="Detailed compliance breakdown for a single device.")
    @action(detail=True, methods=["get"])
    def compliance(self, request, pk=None):
        device = self.get_object()
        serializer = DeviceDetailSerializer(device)
        return Response(serializer.get_compliance_summary(device))

    @extend_schema(summary="List patches", description="List all DevicePatchStatus for this device.")
    @action(detail=True, methods=["get"])
    def patches(self, request, pk=None):
        device = self.get_object()
        statuses = DevicePatchStatus.objects.filter(device=device).select_related('patch')
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
        # In a real app we'd construct a minimal serializer. Using a manual response map here.
        data = [{
            "deployment_id": str(t.deployment.id),
            "deployment_name": t.deployment.name,
            "status": t.status,
            "started_at": t.started_at,
            "completed_at": t.completed_at
        } for t in targets]
        return Response(data)

    @extend_schema(summary="Trigger patch scan", description="Enqueue Celery task to scan for missing patches.")
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def scan(self, request, pk=None):
        device = self.get_object()
        # Simulated scan launch
        return Response({"status": f"Scan triggered for {device.hostname}"}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(summary="Trigger reboot", description="Send reboot command via Redis pub/sub.")
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def reboot(self, request, pk=None):
        device = self.get_object()
        # Simulated reboot topic publish
        return Response({"status": f"Reboot command scheduled for {device.hostname}"}, status=status.HTTP_202_ACCEPTED)

    @extend_schema(summary="Bulk tag devices", description="Bulk add/remove tags on multiple devices.", request=DeviceBulkTagSerializer)
    @action(detail=False, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def bulk_tag(self, request):
        serializer = DeviceBulkTagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        device_ids = serializer.validated_data['device_ids']
        tags_to_apply = serializer.validated_data['tags']
        action_type = serializer.validated_data['action']
        
        devices = Device.objects.filter(id__in=device_ids)
        for dev in devices:
            current_tags = dev.tags or []
            if action_type == 'add':
                dev.tags = list(set(current_tags + tags_to_apply))
            else:
                dev.tags = [t for t in current_tags if t not in tags_to_apply]
            dev.save()
            
        return Response({"status": f"Bulk tag {action_type} completed on {len(devices)} devices"})

    @extend_schema(summary="Bulk group devices", description="Bulk add devices to a group.")
    @action(detail=False, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def bulk_group(self, request):
        device_ids = request.data.get('device_ids', [])
        group_id = request.data.get('group_id')
        try:
            group = DeviceGroup.objects.get(id=group_id)
            devices = Device.objects.filter(id__in=device_ids)
            for dev in devices:
                dev.groups.add(group)
            return Response({"status": f"Added {len(devices)} devices to group {group.name}"})
        except DeviceGroup.DoesNotExist:
            return Response({"error": "Group not found"}, status=status.HTTP_404_NOT_FOUND)

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
