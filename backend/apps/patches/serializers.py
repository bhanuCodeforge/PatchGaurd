from rest_framework import serializers
from .models import Patch, DevicePatchStatus

class PatchListSerializer(serializers.ModelSerializer):
    affected_device_count = serializers.SerializerMethodField()

    class Meta:
        model = Patch
        fields = ['id', 'vendor_id', 'title', 'severity', 'status', 'vendor', 'cve_ids', 'applicable_os', 'requires_reboot', 'released_at', 'affected_device_count']

    def get_affected_device_count(self, obj):
        return DevicePatchStatus.objects.filter(patch=obj, state=DevicePatchStatus.State.MISSING).count()

class PatchDetailSerializer(serializers.ModelSerializer):
    affected_device_count = serializers.SerializerMethodField()
    device_status_breakdown = serializers.SerializerMethodField()
    supersedes_name = serializers.CharField(source='supersedes.vendor_id', read_only=True)
    
    # In a full model, superseded_by is the reverse relation name. If standard reverse foreign key:
    superseded_by_names = serializers.SerializerMethodField()

    class Meta:
        model = Patch
        fields = '__all__'

    def get_affected_device_count(self, obj):
        return DevicePatchStatus.objects.filter(patch=obj, state=DevicePatchStatus.State.MISSING).count()

    def get_device_status_breakdown(self, obj):
        statuses = DevicePatchStatus.objects.filter(patch=obj)
        return {
            'missing': statuses.filter(state=DevicePatchStatus.State.MISSING).count(),
            'pending': statuses.filter(state=DevicePatchStatus.State.PENDING).count(),
            'installed': statuses.filter(state=DevicePatchStatus.State.INSTALLED).count(),
            'failed': statuses.filter(state=DevicePatchStatus.State.FAILED).count(),
        }

    def get_superseded_by_names(self, obj):
        s_by = getattr(obj, 'superseded_by', None)
        if s_by is not None:
             return list(s_by.values_list('vendor_id', flat=True))
        return []

class PatchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patch
        fields = ['vendor_id', 'title', 'severity', 'vendor', 'applicable_os', 'description', 'cve_ids', 'requires_reboot']

class PatchApprovalSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True)

class DevicePatchStatusSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    patch_vendor_id = serializers.CharField(source='patch.vendor_id', read_only=True)
    patch_title = serializers.CharField(source='patch.title', read_only=True)

    class Meta:
        model = DevicePatchStatus
        fields = '__all__'
