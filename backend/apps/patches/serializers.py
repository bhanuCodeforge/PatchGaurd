from rest_framework import serializers
from .models import Patch, DevicePatchStatus

class PatchListSerializer(serializers.ModelSerializer):
    affected_device_count = serializers.SerializerMethodField()

    class Meta:
        model = Patch
        fields = ['id', 'vendor_id', 'title', 'severity', 'status', 'vendor', 'cve_ids', 'cvss_score', 'applicable_os', 'requires_reboot', 'released_at', 'affected_device_count']

    def get_affected_device_count(self, obj):
        return DevicePatchStatus.objects.filter(patch=obj, state=DevicePatchStatus.State.MISSING).count()

class PatchDetailSerializer(serializers.ModelSerializer):
    affected_device_count = serializers.SerializerMethodField()
    device_status_breakdown = serializers.SerializerMethodField()
    supersedes_name = serializers.CharField(source='supersedes.vendor_id', read_only=True)
    
    # In a full model, superseded_by is the reverse relation name. If standard reverse foreign key:
    superseded_by_names = serializers.SerializerMethodField()
    approved_by_name = serializers.CharField(source='approved_by.full_name', read_only=True, default='')

    class Meta:
        model = Patch
        fields = [
            'id', 'vendor_id', 'title', 'description', 'severity', 'status',
            'vendor', 'kb_article', 'cve_ids', 'cvss_score', 'applicable_os', 
            'package_name', 'package_version', 'file_url', 'requires_reboot',
            'approved_by', 'approved_by_name', 'approved_at', 'status_notes',
            'released_at', 'created_at', 'updated_at',
            'affected_device_count', 'device_status_breakdown',
            'supersedes_name', 'superseded_by_names'
        ]

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

class BulkPatchActionSerializer(serializers.Serializer):
    patch_ids = serializers.ListField(child=serializers.UUIDField())
    reason = serializers.CharField(required=False, allow_blank=True)

class DevicePatchStatusSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)
    patch_vendor_id = serializers.CharField(source='patch.vendor_id', read_only=True)
    patch_title = serializers.CharField(source='patch.title', read_only=True)
    patch = serializers.SerializerMethodField()

    class Meta:
        model = DevicePatchStatus
        fields = [
            'id', 'device', 'patch', 'state', 'execution_lane',
            'execution_duration_ms', 'installed_at', 'error_message',
            'retry_count', 'last_attempt', 'device_hostname',
            'patch_vendor_id', 'patch_title',
        ]

    def get_patch(self, obj):
        p = obj.patch
        return {
            'id': str(p.id),
            'vendor_id': p.vendor_id,
            'title': p.title,
            'severity': p.severity,
            'status': p.status,
            'vendor': p.vendor,
            'kb_article': p.kb_article,
            'cve_ids': p.cve_ids or [],
            'cvss_score': p.cvss_score,
            'requires_reboot': p.requires_reboot,
            'package_name': p.package_name,
            'package_version': p.package_version,
            'released_at': p.released_at,
        }
