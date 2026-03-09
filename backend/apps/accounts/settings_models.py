from django.db import models
import uuid

class SystemSetting(models.Model):
    """
    Global system settings for PatchGuard 1.0 parity.
    Stored as key-value pairs with optional JSON data.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "system_setting"

    @classmethod
    def get_value(cls, key: str, default: str = "") -> str:
        try:
            return cls.objects.get(key=key).value
        except cls.DoesNotExist:
            return default

    @classmethod
    def get_bool(cls, key: str, default: bool = False) -> bool:
        val = cls.get_value(key)
        if not val:
            return default
        return val.lower() in ("true", "1", "yes", "on")

    @classmethod
    def get_data(cls, key: str, default: dict = None) -> dict:
        try:
            return cls.objects.get(key=key).data
        except cls.DoesNotExist:
            return default or {}

    def __str__(self):
        return self.key
