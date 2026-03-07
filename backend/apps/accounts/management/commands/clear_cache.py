from django.core.management.base import BaseCommand
from django.core.cache import cache

class Command(BaseCommand):
    help = "Clear all entries from the Redis cache."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Clearing application cache..."))
        try:
            cache.clear()
            self.stdout.write(self.style.SUCCESS("  - Cache: CLEARED"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - Cache: FAILED ({e})"))
