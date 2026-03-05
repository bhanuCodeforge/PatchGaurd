from django.contrib import admin
from .models import DeviceGroup, Device

@admin.register(DeviceGroup)
class DeviceGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "is_dynamic", "parent", "created_at")
    search_fields = ("name", "description")
    list_filter = ("is_dynamic",)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("hostname", "ip_address", "os_family", "environment", "status", "last_seen")
    list_filter = ("os_family", "environment", "status")
    search_fields = ("hostname", "ip_address", "mac_address")
    filter_horizontal = ("groups",)
    readonly_fields = ("created_at", "updated_at", "last_seen", "last_checkin_ip")
