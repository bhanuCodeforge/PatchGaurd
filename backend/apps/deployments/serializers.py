from rest_framework import serializers
from .models import Deployment, DeploymentTarget
from apps.patches.serializers import PatchListSerializer
from apps.inventory.serializers import DeviceGroupSerializer

class DeploymentListSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.ReadOnlyField()
    failure_rate = serializers.ReadOnlyField()
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = Deployment
        fields = [
            'id', 'name', 'status', 'strategy', 'total_devices', 'completed_devices', 
            'failed_devices', 'current_wave', 'created_by_name', 'created_at', 
            'started_at', 'completed_at', 'progress_percentage', 'failure_rate'
        ]

class DeploymentDetailSerializer(serializers.ModelSerializer):
    patches = PatchListSerializer(many=True, read_only=True)
    target_groups = DeviceGroupSerializer(many=True, read_only=True)
    progress_percentage = serializers.ReadOnlyField()
    failure_rate = serializers.ReadOnlyField()
    wave_summary = serializers.SerializerMethodField()
    target_breakdown = serializers.SerializerMethodField()

    class Meta:
        model = Deployment
        fields = '__all__'

    def get_wave_summary(self, obj):
        from django.db.models import Count
        # Simple wave aggregation
        qs = DeploymentTarget.objects.filter(deployment=obj).values('wave_number').annotate(total=Count('id'))
        
        waves = []
        for w in qs:
            num = w['wave_number']
            w_targets = DeploymentTarget.objects.filter(deployment=obj, wave_number=num)
            waves.append({
                'wave_number': num,
                'total': w['total'],
                'completed': w_targets.filter(status=DeploymentTarget.Status.COMPLETED).count(),
                'failed': w_targets.filter(status=DeploymentTarget.Status.FAILED).count(),
                'in_progress': w_targets.filter(status=DeploymentTarget.Status.IN_PROGRESS).count(),
            })
        return waves

    def get_target_breakdown(self, obj):
        targets = DeploymentTarget.objects.filter(deployment=obj)
        return {
            'queued': targets.filter(status=DeploymentTarget.Status.QUEUED).count(),
            'in_progress': targets.filter(status=DeploymentTarget.Status.IN_PROGRESS).count(),
            'completed': targets.filter(status=DeploymentTarget.Status.COMPLETED).count(),
            'failed': targets.filter(status=DeploymentTarget.Status.FAILED).count(),
            'skipped': targets.filter(status=DeploymentTarget.Status.SKIPPED).count()
        }

class DeploymentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Deployment
        fields = [
            'name', 'description', 'strategy', 'canary_percentage', 'wave_size', 
            'wave_delay_minutes', 'max_failure_percentage', 'requires_reboot', 
            'maintenance_window_start', 'maintenance_window_end', 'scheduled_at',
            'patches', 'target_groups'
        ]

    def validate(self, attrs):
        if 'patches' in attrs and not attrs['patches']:
            raise serializers.ValidationError({"patches": "At least one patch is required."})
        if 'target_groups' in attrs and not attrs['target_groups']:
            raise serializers.ValidationError({"target_groups": "At least one target group is required."})
        
        # Validate patches are approved
        from apps.patches.models import Patch
        for patch in attrs.get('patches', []):
            if patch.status != Patch.Status.APPROVED:
                raise serializers.ValidationError({"patches": f"Patch {patch.vendor_id} must be APPROVED."})

        return attrs

class DeploymentTargetSerializer(serializers.ModelSerializer):
    device_hostname = serializers.CharField(source='device.hostname', read_only=True)

    class Meta:
        model = DeploymentTarget
        fields = ['id', 'device', 'device_hostname', 'wave_number', 'status', 'started_at', 'completed_at', 'error_log']
