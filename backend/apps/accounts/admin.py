from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, AuditLog

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "role", "department", "is_active", "last_login")
    list_filter = ("role", "is_active", "is_ldap_user")
    search_fields = ("username", "email", "department")
    readonly_fields = ("last_login", "date_joined", "failed_login_attempts", "locked_until", "last_password_change")

    fieldsets = BaseUserAdmin.fieldsets + (
        ("PatchGuard Profile", {
            "fields": ("role", "department", "is_ldap_user", "ldap_dn")
        }),
        ("Security", {
            "fields": ("must_change_password", "last_password_change", "failed_login_attempts", "locked_until")
        }),
    )

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user", "action", "resource_type", "ip_address")
    list_filter = ("action", "resource_type")
    search_fields = ("user__username", "action", "resource_id")
    date_hierarchy = "timestamp"
    
    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False
