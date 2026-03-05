from django.contrib import admin
from .models import Patch, DevicePatchStatus

@admin.register(Patch)
class PatchAdmin(admin.ModelAdmin):
    list_display = ("vendor_id", "title", "severity", "status", "vendor", "requires_reboot", "released_at")
    list_filter = ("severity", "status", "vendor", "requires_reboot")
    search_fields = ("vendor_id", "title", "cve_ids")
    actions = ["approve_patches", "reject_patches"]

    @admin.action(description="Mark selected patches as approved")
    def approve_patches(self, request, queryset):
        queryset.update(status=Patch.Status.APPROVED, approved_by=request.user)

    @admin.action(description="Mark selected patches as rejected")
    def reject_patches(self, request, queryset):
        queryset.update(status=Patch.Status.REJECTED)


@admin.register(DevicePatchStatus)
class DevicePatchStatusAdmin(admin.ModelAdmin):
    list_display = ("device", "patch", "state", "installed_at", "retry_count")
    list_filter = ("state",)
    raw_id_fields = ("device", "patch")
