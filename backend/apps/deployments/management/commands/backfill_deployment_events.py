"""
Management command: backfill_deployment_events

Backfills DeploymentEvent rows from existing DeploymentTarget records so the
event log is consistent for deployments that ran before Task 11.5 was deployed.

Usage:
    python manage.py backfill_deployment_events
    python manage.py backfill_deployment_events --dry-run
    python manage.py backfill_deployment_events --deployment-id <uuid>
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.deployments.models import Deployment, DeploymentTarget, DeploymentEvent


class Command(BaseCommand):
    help = "Backfill DeploymentEvent rows from existing DeploymentTarget records."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created without writing to DB")
        parser.add_argument("--deployment-id", type=str, help="Only backfill a specific deployment UUID")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        dep_id = options.get("deployment_id")

        qs = Deployment.objects.all()
        if dep_id:
            qs = qs.filter(id=dep_id)

        total_created = 0

        for deployment in qs.iterator():
            existing_types = set(
                DeploymentEvent.objects.filter(deployment=deployment)
                .values_list("event_type", "target_id")
            )

            targets = DeploymentTarget.objects.filter(deployment=deployment).select_related("device")
            events_to_create = []

            for target in targets:
                # QUEUED event
                if ("queued", target.id) not in existing_types:
                    events_to_create.append(DeploymentEvent(
                        deployment=deployment,
                        target=target,
                        device=target.device,
                        event_type=DeploymentEvent.EventType.QUEUED,
                        wave_number=target.wave_number,
                        detail={},
                    ))

                # STARTED event
                if target.started_at and ("started", target.id) not in existing_types:
                    events_to_create.append(DeploymentEvent(
                        deployment=deployment,
                        target=target,
                        device=target.device,
                        event_type=DeploymentEvent.EventType.STARTED,
                        wave_number=target.wave_number,
                        detail={},
                    ))

                # Terminal event
                terminal_map = {
                    DeploymentTarget.Status.COMPLETED:  DeploymentEvent.EventType.COMPLETED,
                    DeploymentTarget.Status.FAILED:     DeploymentEvent.EventType.FAILED,
                    DeploymentTarget.Status.SKIPPED:    DeploymentEvent.EventType.SKIPPED,
                }
                terminal_type = terminal_map.get(target.status)
                if terminal_type and (terminal_type, target.id) not in existing_types:
                    events_to_create.append(DeploymentEvent(
                        deployment=deployment,
                        target=target,
                        device=target.device,
                        event_type=terminal_type,
                        wave_number=target.wave_number,
                        detail={"error_log": target.error_log} if target.error_log else {},
                    ))

            if events_to_create:
                self.stdout.write(
                    f"Deployment {deployment.id} ({deployment.name}): "
                    f"{'[DRY RUN] would create' if dry_run else 'creating'} {len(events_to_create)} events"
                )
                if not dry_run:
                    with transaction.atomic():
                        DeploymentEvent.objects.bulk_create(events_to_create, ignore_conflicts=True)
                total_created += len(events_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {'Would have created' if dry_run else 'Created'} {total_created} DeploymentEvent rows."
            )
        )
