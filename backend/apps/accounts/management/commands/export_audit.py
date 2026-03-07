import csv
import os
from django.core.management.base import BaseCommand
from apps.accounts.models import AuditLog

class Command(BaseCommand):
    help = "Export the system audit log to a CSV file for long-term storage or compliance."

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default='audit_export.csv',
            help='Output file path.',
        )

    def handle(self, *args, **options):
        output_file = options.get('output')
        self.stdout.write(self.style.WARNING(f"Exporting audit logs to {output_file}..."))

        fields = [
            'id', 'user__username', 'action', 'resource', 'resource_id', 'ip_address', 'timestamp'
        ]

        try:
            logs = AuditLog.objects.select_related('user').all().values_list(*fields)
            
            with open(output_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(fields) # Header
                writer.writerows(logs)

            self.stdout.write(self.style.SUCCESS(f"  - Audit Export: COMPLETED ({len(logs)} records written)"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - Audit Export: FAILED ({e})"))
