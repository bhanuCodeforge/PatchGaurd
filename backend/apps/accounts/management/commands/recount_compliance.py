from django.core.management.base import BaseCommand
from apps.inventory.tasks import refresh_all_device_compliance

class Command(BaseCommand):
    help = "Manually trigger a full recount of device compliance health scores."

    def add_arguments(self, parser):
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run the task asynchronously using Celery.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Recounting compliance for all devices..."))
        try:
            if options.get('async'):
                task = refresh_all_device_compliance.delay()
                self.stdout.write(self.style.SUCCESS(f"  - Compliance Recount: QUEUED (Task ID: {task.id})"))
            else:
                refresh_all_device_compliance()
                self.stdout.write(self.style.SUCCESS("  - Compliance Recount: COMPLETED"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - Compliance Recount: FAILED ({e})"))
