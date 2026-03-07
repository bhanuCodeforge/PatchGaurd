import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django_redis import get_redis_connection

class Command(BaseCommand):
    help = "Verify the system health of all PatchGuard platform components."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("--- PatchGuard Platform Verification ---"))

        # 1. Database Check
        self.stdout.write("1. Database (PostgreSQL)... ", ending="")
        try:
            connection.ensure_connection()
            self.stdout.write(self.style.SUCCESS("OK"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAILED ({e})"))

        # 2. Redis Check
        self.stdout.write("2. Cache/Broker (Redis)... ", ending="")
        try:
            redis_conn = get_redis_connection("default")
            redis_conn.ping()
            self.stdout.write(self.style.SUCCESS("OK"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAILED ({e})"))

        # 3. Realtime Service Check
        self.stdout.write("3. Realtime Service (FastAPI)... ", ending="")
        try:
            # Assume realtime service is on port 8001
            # In a production environment, this would be a config variable
            realtime_url = "http://localhost:8001/health/"
            response = requests.get(realtime_url, timeout=5)
            if response.status_code == 200:
                self.stdout.write(self.style.SUCCESS("OK"))
            else:
                self.stdout.write(self.style.WARNING(f"UNHEALTHY ({response.status_code})"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAILED ({e})"))

        # 4. Celery Worker Check (Passive)
        self.stdout.write("4. Celery Worker Pool... ", ending="")
        # Simple ping to celery app
        from config.celery_app import app as celery_app
        try:
            i = celery_app.control.inspect()
            stats = i.stats()
            if stats:
                self.stdout.write(self.style.SUCCESS(f"OK ({len(stats)} workers)"))
            else:
                self.stdout.write(self.style.WARNING("NO WORKERS FOUND"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"FAILED ({e})"))

        self.stdout.write(self.style.MIGRATE_HEADING("--- Verification Complete ---"))
