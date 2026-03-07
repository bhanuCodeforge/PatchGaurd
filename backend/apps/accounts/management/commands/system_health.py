import os
import shutil
import psutil
from django.core.management.base import BaseCommand
from django.db import connection
from django.core.cache import cache
from django.conf import settings

class Command(BaseCommand):
    help = "Perform a deep-dive diagnostic check of the PatchGuard system health."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- PatchGuard System Health ---"))

        # 1. Database Check
        self.stdout.write(self.style.SUCCESS("\n[Database]"))
        try:
            connection.ensure_connection()
            db_name = settings.DATABASES['default']['NAME']
            self.stdout.write(f"  - Connection: OK")
            self.stdout.write(f"  - Database: {db_name}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - Connection: FAILED ({e})"))

        # 2. Redis/Cache Check
        self.stdout.write(self.style.SUCCESS("\n[Cache/Redis]"))
        try:
            cache.set("health_check_key", "ok", timeout=10)
            val = cache.get("health_check_key")
            if val == "ok":
                self.stdout.write(f"  - Redis Connection: OK")
            else:
                self.stdout.write(self.style.ERROR(f"  - Redis Connection: DATA INCONSISTENCY"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - Redis Connection: FAILED ({e})"))

        # 3. Disk Space Check
        self.stdout.write(self.style.SUCCESS("\n[Storage]"))
        total, used, free = shutil.disk_usage("/")
        free_gb = free // (2**30)
        self.stdout.write(f"  - Root Free Space: {free_gb} GB")
        if free_gb < 5:
            self.stdout.write(self.style.WARNING("  - Warning: Low disk space (< 5GB)"))

        # 4. Memory Check
        self.stdout.write(self.style.SUCCESS("\n[Resources]"))
        mem = psutil.virtual_memory()
        self.stdout.write(f"  - Memory Usage: {mem.percent}% ({mem.used // (2**20)}MB / {mem.total // (2**20)}MB)")
        if mem.percent > 90:
            self.stdout.write(self.style.WARNING("  - Warning: Memory usage is critically high"))

        # 5. Directory Check
        self.stdout.write(self.style.SUCCESS("\n[Filesystem]"))
        log_dir = os.getenv("LOG_DIR", "/var/log/patchmgr")
        if os.path.exists(log_dir):
            self.stdout.write(f"  - Log Directory: {log_dir} (OK)")
        else:
            self.stdout.write(self.style.WARNING(f"  - Log Directory: {log_dir} (MISSING)"))

        self.stdout.write(self.style.MIGRATE_HEADING("\n--- Diagnostic Complete ---"))
