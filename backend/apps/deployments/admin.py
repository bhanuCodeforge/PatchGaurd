from django.contrib import admin
from .models import Deployment, DeploymentTarget

class DeploymentTargetInline(admin.TabularInline):
    model = DeploymentTarget
    extra = 0
    raw_id_fields = ("device",)
    readonly_fields = ("status", "started_at", "completed_at", "error_log")
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Limit the number of inline items to avoid performance issues with large deployments
        return qs[:20]

@admin.register(Deployment)
class DeploymentAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "strategy", "total_devices", "completed_devices", "failed_devices", "created_by", "created_at")
    list_filter = ("status", "strategy")
    search_fields = ("name", "description")
    readonly_fields = ("total_devices", "completed_devices", "failed_devices", "current_wave")
    filter_horizontal = ("patches", "target_groups")
    inlines = [DeploymentTargetInline]

@admin.register(DeploymentTarget)
class DeploymentTargetAdmin(admin.ModelAdmin):
    list_display = ("deployment", "device", "wave_number", "status", "started_at", "completed_at")
    list_filter = ("status", "wave_number")
    search_fields = ("deployment__name", "device__hostname")
    raw_id_fields = ("deployment", "device")
