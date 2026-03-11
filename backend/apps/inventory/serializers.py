from rest_framework import serializers
from .models import Device, DeviceGroup, DeviceEvent
import string
import secrets
import uuid

class DeviceGroupSerializer(serializers.ModelSerializer):
    device_count = serializers.SerializerMethodField()
    parent_name = serializers.CharField(source='parent.name', read_only=True)
    children = serializers.SerializerMethodField()

    class Meta:
        model = DeviceGroup
        fields = ['id', 'name', 'description', 'dynamic_rules', 'is_dynamic', 'parent', 'parent_name', 'children', 'created_at', 'updated_at', 'device_count']

    def get_device_count(self, obj):
        return obj.get_devices().count()

    def get_children(self, obj):
        children = DeviceGroup.objects.filter(parent=obj)
        if not children.exists():
            return []
        return DeviceGroupSerializer(children, many=True, context=self.context).data

class DeviceGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceGroup
        fields = ['name', 'description', 'is_dynamic', 'dynamic_rules', 'parent']

class DeviceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = [
            'id', 'hostname', 'description', 'ip_address', 'mac_address', 
            'os_family', 'os_version', 'os_arch', 'environment', 'status', 
            'tags', 'agent_version', 'last_seen', 'compliance_rate', 'metadata'
        ]

class DeviceDetailSerializer(serializers.ModelSerializer):
    groups = DeviceGroupSerializer(many=True, read_only=True)
    compliance_summary = serializers.SerializerMethodField()
    patch_stats = serializers.SerializerMethodField()

    class Meta:
        model = Device
        fields = [
            'id', 'hostname', 'description', 'ip_address', 'mac_address',
            'os_family', 'os_version', 'os_arch', 'agent_version',
            'environment', 'status', 'tags', 'groups', 'metadata',
            'compliance_rate', 'inventory_data', 'lane_config',
            'last_seen', 'last_scan', 'created_at',
            'compliance_summary', 'patch_stats', 'os_name',
            'key_created_at', 'key_last_rotated_at',
        ]

    def get_compliance_summary(self, obj):
        from apps.patches.models import DevicePatchStatus
        statuses = DevicePatchStatus.objects.filter(device=obj)
        counts = {'total': statuses.count()}
        for choice in DevicePatchStatus.State.choices:
            state_val = choice[0]
            counts[state_val] = statuses.filter(state=state_val).count()
        return counts

    def get_patch_stats(self, obj):
        from apps.patches.models import DevicePatchStatus
        statuses = DevicePatchStatus.objects.filter(device=obj)
        return {
            'total': statuses.count(),
            'installed': statuses.filter(state=DevicePatchStatus.State.INSTALLED).count(),
            'missing': statuses.filter(state=DevicePatchStatus.State.MISSING).count(),
            'pending': statuses.filter(state=DevicePatchStatus.State.PENDING).count(),
            'failed': statuses.filter(state=DevicePatchStatus.State.FAILED).count(),
            'pending_reboot': statuses.filter(state=DevicePatchStatus.State.PENDING_REBOOT).count(),
        }

class DeviceCreateSerializer(serializers.ModelSerializer):
    # os_version, agent_version, and hostname are optional from the UI
    hostname      = serializers.CharField(required=False, default='', allow_blank=True)
    os_version    = serializers.CharField(required=False, default='', allow_blank=True)
    agent_version = serializers.CharField(required=False, default='', allow_blank=True)

    class Meta:
        model = Device
        fields = ['hostname', 'description', 'ip_address', 'os_family', 'os_version', 'mac_address', 'os_arch', 'environment', 'status', 'tags', 'agent_version']

    def create(self, validated_data):
        if not validated_data.get('hostname'):
            validated_data['hostname'] = f"pending-{uuid.uuid4().hex[:8]}"
            
        alphabet = string.ascii_letters + string.digits
        api_key = ''.join(secrets.choice(alphabet) for i in range(32))
        validated_data['agent_api_key'] = api_key
        return super().create(validated_data)

class DeviceBulkTagSerializer(serializers.Serializer):
    device_ids = serializers.ListField(child=serializers.UUIDField())
    tags = serializers.ListField(child=serializers.CharField())
    action = serializers.ChoiceField(choices=['add', 'remove'])


class DeviceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceEvent
        fields = [
            'id', 'device', 'event_type', 'severity', 'message',
            'details', 'source', 'deployment_id', 'patch_id',
            'execution_lane', 'created_at',
        ]
        read_only_fields = fields


class LaneConfigSerializer(serializers.Serializer):
    """Validates lane configuration payload before pushing to agent."""
    fast_lane = serializers.DictField(required=False)
    slow_lane = serializers.DictField(required=False)

    def validate_fast_lane(self, value):
        allowed = {
            'interval', 'concurrency',
            'max_bandwidth_mbps', 'bandwidth_kbps',
            'retry_count', 'retry_delay_sec', 'retry_strategy',
            'rate_limit',
        }
        for key in value:
            if key not in allowed:
                raise serializers.ValidationError(f"Unknown fast_lane key: {key}")
        if 'interval' in value and (not isinstance(value['interval'], (int, float)) or value['interval'] < 1):
            raise serializers.ValidationError("fast_lane.interval must be >= 1")
        if 'concurrency' in value and (not isinstance(value['concurrency'], int) or value['concurrency'] < 1):
            raise serializers.ValidationError("fast_lane.concurrency must be >= 1")
        if 'rate_limit' in value and (not isinstance(value['rate_limit'], (int, float)) or value['rate_limit'] < 0):
            raise serializers.ValidationError("fast_lane.rate_limit must be >= 0")
        return value

    def validate_slow_lane(self, value):
        allowed = {
            'interval', 'concurrency',
            'max_bandwidth_mbps', 'bandwidth_kbps',
            'retry_count', 'retry_delay_sec', 'retry_strategy',
            'rate_limit',
        }
        for key in value:
            if key not in allowed:
                raise serializers.ValidationError(f"Unknown slow_lane key: {key}")
        if 'interval' in value and (not isinstance(value['interval'], (int, float)) or value['interval'] < 60):
            raise serializers.ValidationError("slow_lane.interval must be >= 60")
        if 'concurrency' in value and (not isinstance(value['concurrency'], int) or value['concurrency'] < 1):
            raise serializers.ValidationError("slow_lane.concurrency must be >= 1")
        if 'rate_limit' in value and (not isinstance(value['rate_limit'], (int, float)) or value['rate_limit'] < 0):
            raise serializers.ValidationError("slow_lane.rate_limit must be >= 0")
        return value


class InstallPatchSerializer(serializers.Serializer):
    """Validates per-patch install request."""
    patch_id = serializers.UUIDField()
    lane = serializers.ChoiceField(choices=['fast', 'slow'], default='fast')
