"""
Task 11.4 — Celery Task Hierarchy Refactor

Implements a two-level task hierarchy:
  orchestrate_deployment  →  execute_wave  →  report_device_result

Design:
  - orchestrate_deployment: idempotent orchestrator, persists minimal state in DB
  - execute_wave: processes one wave of devices, 15-min timeout per wave
  - report_device_result: atomic counter update per device result (no race condition)
  - Dedicated queues: critical / deployment-waves / deployment-results
  - Stuck-wave monitoring: waves pending > WAVE_TIMEOUT_MINUTES flagged as stuck

Replaces the monolithic execute_deployment task.
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
import time
import logging

from .models import Deployment, DeploymentTarget
from common.redis_pubsub import RedisPublisher

logger = logging.getLogger(__name__)

# Timeouts
WAVE_SOFT_LIMIT = 900   # 15 min soft limit — wave should complete by now
WAVE_HARD_LIMIT = 1200  # 20 min hard limit — kill stuck wave
WAVE_TIMEOUT_MINUTES = 25  # threshold for "stuck wave" monitoring

# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────

def _publish_progress(deployment: Deployment) -> None:
    """Broadcast current deployment progress over Redis."""
    RedisPublisher.publish_deployment_progress(str(deployment.id), {
        "status": deployment.status,
        "current_wave": deployment.current_wave,
        "total_devices": deployment.total_devices,
        "completed_devices": deployment.completed_devices,
        "failed_devices": deployment.failed_devices,
        "progress_percentage": deployment.progress_percentage,
        "failure_rate": deployment.failure_rate,
    })


def _build_wave_targets(deployment: Deployment) -> None:
    """
    Partition devices from all target groups into waves and bulk-create
    DeploymentTarget rows.  Idempotent: skips if targets already exist.
    """
    if DeploymentTarget.objects.filter(deployment=deployment).exists():
        return

    device_ids = set()
    for group in deployment.target_groups.all():
        for dev_id in group.get_devices().values_list("id", flat=True):
            device_ids.add(dev_id)

    devices = list(device_ids)
    total = len(devices)

    if total == 0:
        deployment.status = Deployment.Status.COMPLETED
        deployment.completed_at = timezone.now()
        deployment.save(update_fields=["status", "completed_at"])
        return

    targets = []
    if deployment.strategy == Deployment.Strategy.IMMEDIATE:
        targets = [DeploymentTarget(deployment=deployment, device_id=d, wave_number=0) for d in devices]
    elif deployment.strategy == Deployment.Strategy.CANARY:
        canary_n = max(1, int(total * (deployment.canary_percentage / 100)))
        for d in devices[:canary_n]:
            targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=0))
        sz = deployment.wave_size or 50
        for w, i in enumerate(range(0, len(devices[canary_n:]), sz), start=1):
            for d in devices[canary_n:][i : i + sz]:
                targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=w))
    else:  # ROLLING / MAINTENANCE
        sz = deployment.wave_size or 50
        for w, i in enumerate(range(0, total, sz)):
            for d in devices[i : i + sz]:
                targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=w))

    DeploymentTarget.objects.bulk_create(targets, ignore_conflicts=True)

    total = DeploymentTarget.objects.filter(deployment=deployment).count()
    deployment.total_devices = total
    deployment.save(update_fields=["total_devices"])


# ───────────────────────────────────────────────────────────────────────────
# Task 1 of 3 — Orchestrator (idempotent)
# ───────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    queue="critical",
    max_retries=5,
    default_retry_delay=30,
    name="apps.deployments.tasks.orchestrate_deployment",
)
def orchestrate_deployment(self, deployment_id: str) -> str:
    """
    Top-level orchestrator.  Re-entrant: safe to call multiple times.

    Responsibilities:
      - Build wave targets (once, idempotent)
      - Iterate waves in order, scheduling execute_wave tasks
      - Check failure threshold BEFORE each wave
      - Mark deployment completed/failed when all waves done
    """
    try:
        deployment = Deployment.objects.select_for_update().get(id=deployment_id)
    except Deployment.DoesNotExist:
        logger.error("orchestrate_deployment: deployment %s not found", deployment_id)
        return "NOT_FOUND"

    with transaction.atomic():
        if deployment.status != Deployment.Status.IN_PROGRESS:
            logger.warning(
                "orchestrate_deployment: %s is not IN_PROGRESS (status=%s), aborting",
                deployment_id, deployment.status,
            )
            return f"SKIP:{deployment.status}"

        _build_wave_targets(deployment)
        deployment.refresh_from_db()

        if deployment.status == Deployment.Status.COMPLETED:
            return "NO_TARGETS"

    # Get distinct wave numbers
    wave_numbers = list(
        DeploymentTarget.objects.filter(deployment=deployment)
        .values_list("wave_number", flat=True)
        .distinct()
        .order_by("wave_number")
    )

    patch_ids = list(deployment.patches.values_list("vendor_id", flat=True))

    for wave_num in wave_numbers:
        # Re-check live status before each wave
        deployment.refresh_from_db()
        if deployment.status != Deployment.Status.IN_PROGRESS:
            logger.info("Orchestrator: deployment %s halted at wave %d", deployment_id, wave_num)
            return f"HALTED_AT_WAVE:{wave_num}"

        # Check skip already-completed waves (re-entrant support)
        pending = DeploymentTarget.objects.filter(
            deployment=deployment,
            wave_number=wave_num,
            status=DeploymentTarget.Status.QUEUED,
        ).exists()
        if not pending:
            logger.debug("Wave %d already processed, skipping", wave_num)
            continue

        # Check failure threshold
        deployment.refresh_from_db()
        if deployment.failure_rate > deployment.max_failure_percentage:
            with transaction.atomic():
                deployment.status = Deployment.Status.FAILED
                deployment.completed_at = timezone.now()
                deployment.save(update_fields=["status", "completed_at"])
            RedisPublisher.publish_notification("error",
                f"Deployment '{deployment.name}' halted — failure rate {deployment.failure_rate:.1f}% exceeds threshold")
            _publish_progress(deployment)
            return "FAILED:THRESHOLD"

        with transaction.atomic():
            deployment.current_wave = wave_num
            deployment.save(update_fields=["current_wave"])

        _publish_progress(deployment)

        # Execute the wave synchronously (blocking — orchestrator owns the loop)
        logger.info("Orchestrator: dispatching wave %d for deployment %s", wave_num, deployment_id)
        execute_wave(deployment_id, wave_num, patch_ids)

        # Enforce inter-wave delay (unless immediate strategy or last wave)
        if (wave_num < max(wave_numbers)
                and deployment.strategy != Deployment.Strategy.IMMEDIATE
                and deployment.wave_delay_minutes):
            delay_sec = max(30, deployment.wave_delay_minutes * 60)
            logger.info("Orchestrator: wave delay %ds before wave %d", delay_sec, wave_num + 1)
            time.sleep(delay_sec)

    # All waves processed
    deployment.refresh_from_db()
    all_done = not DeploymentTarget.objects.filter(
        deployment=deployment,
        status=DeploymentTarget.Status.QUEUED,
    ).exists()

    if all_done:
        with transaction.atomic():
            failed_count = DeploymentTarget.objects.filter(
                deployment=deployment, status=DeploymentTarget.Status.FAILED
            ).count()
            deployment.status = (
                Deployment.Status.FAILED if failed_count > 0 and deployment.failure_rate > deployment.max_failure_percentage
                else Deployment.Status.COMPLETED
            )
            deployment.completed_at = timezone.now()
            deployment.save(update_fields=["status", "completed_at"])

    deployment.refresh_from_db()
    _publish_progress(deployment)
    logger.info("Orchestrator: deployment %s finished with status %s", deployment_id, deployment.status)
    return f"DONE:{deployment.status}"


# ───────────────────────────────────────────────────────────────────────────
# Task 2 of 3 — Wave executor
# ───────────────────────────────────────────────────────────────────────────

@shared_task(
    bind=True,
    queue="deployment-waves",
    soft_time_limit=WAVE_SOFT_LIMIT,
    time_limit=WAVE_HARD_LIMIT,
    name="apps.deployments.tasks.execute_wave",
)
def execute_wave(self, deployment_id: str, wave_number: int, patch_ids: list) -> dict:
    """
    Execute one wave: run pre-flight checks then dispatch patch commands to agents.

    Idempotent: if all targets are already past QUEUED, returns immediately.
    A crash here loses at most ONE wave (not the entire deployment).
    """
    try:
        deployment = Deployment.objects.get(id=deployment_id)
    except Deployment.DoesNotExist:
        return {"status": "NOT_FOUND", "wave": wave_number}

    queued_targets = DeploymentTarget.objects.filter(
        deployment=deployment,
        wave_number=wave_number,
        status=DeploymentTarget.Status.QUEUED,
    ).select_related("device")

    if not queued_targets.exists():
        return {"status": "ALREADY_DONE", "wave": wave_number}

    # ── Pre-flight health checks ──────────────────────────────────────────
    request_id = f"preflight_{deployment_id}_{wave_number}_{int(time.time())}"
    for t in queued_targets:
        RedisPublisher.publish_agent_command(str(t.device.id), "HEALTH_CHECK", {"request_id": request_id})

    # Poll up to 60s for health reports
    deadline = timezone.now() + timezone.timedelta(seconds=60)
    while timezone.now() < deadline:
        all_in = True
        for t in queued_targets:
            t.device.refresh_from_db()
            hc = (t.device.metadata or {}).get("last_health_check", {})
            ts = hc.get("timestamp", "")
            cutoff = str(timezone.now() - timezone.timedelta(seconds=90))
            if not ts or ts < cutoff:
                all_in = False
                break
        if all_in:
            break
        time.sleep(3)

    # ── Evaluate pre-flight, skip unhealthy devices ───────────────────────
    skipped = 0
    for t in queued_targets:
        t.device.refresh_from_db()
        hc = (t.device.metadata or {}).get("last_health_check", {}) if t.device.metadata else {}
        disk_free = hc.get("disk_free_pct", 100)
        cpu_busy = hc.get("cpu_pct", 0)
        mem_used = hc.get("memory_pct", 0)
        if disk_free < 10 or cpu_busy > 95 or mem_used > 95:
            t.status = DeploymentTarget.Status.SKIPPED
            t.error_log = f"Preflight: disk={disk_free}% cpu={cpu_busy}% mem={mem_used}%"
            t.completed_at = timezone.now()
            t.save(update_fields=["status", "error_log", "completed_at"])
            skipped += 1
            logger.warning("Wave %d: skipping %s — preflight failed", wave_number, t.device.hostname)

    # ── Dispatch patch command to healthy devices ─────────────────────────
    dispatched = 0
    re_queried = DeploymentTarget.objects.filter(
        deployment=deployment,
        wave_number=wave_number,
        status=DeploymentTarget.Status.QUEUED,
    ).select_related("device")

    for t in re_queried:
        with transaction.atomic():
            t.status = DeploymentTarget.Status.IN_PROGRESS
            t.started_at = timezone.now()
            t.save(update_fields=["status", "started_at"])

        RedisPublisher.publish_agent_command(
            str(t.device.id),
            "START_DEPLOYMENT",
            {
                "deployment_id": str(deployment_id),
                "target_id": str(t.id),
                "patches": patch_ids,
            },
        )
        dispatched += 1

    logger.info("Wave %d: dispatched=%d skipped=%d for deployment %s",
                wave_number, dispatched, skipped, deployment_id)

    return {"status": "DISPATCHED", "wave": wave_number, "dispatched": dispatched, "skipped": skipped}


# ───────────────────────────────────────────────────────────────────────────
# Task 3 of 3 — Per-device result reporter
# ───────────────────────────────────────────────────────────────────────────

@shared_task(
    queue="deployment-results",
    name="apps.deployments.tasks.report_device_result",
    acks_late=True,
    reject_on_worker_lost=True,
)
def report_device_result(deployment_id: str, target_id: str, success: bool, error_log: str = "") -> dict:
    """
    Atomically record a device result and update deployment counters.

    Called by the agent webhook (ingest_patch_result) after a device
    finishes patching.  Using F() expressions prevents the race condition
    on completed_devices / failed_devices that the monolithic task had.
    """
    from django.db.models import F

    try:
        target = DeploymentTarget.objects.select_related("deployment").get(id=target_id)
    except DeploymentTarget.DoesNotExist:
        logger.warning("report_device_result: target %s not found", target_id)
        return {"status": "NOT_FOUND"}

    if target.status not in (DeploymentTarget.Status.IN_PROGRESS, DeploymentTarget.Status.QUEUED):
        return {"status": "ALREADY_RECORDED", "target_id": target_id}

    new_status = DeploymentTarget.Status.COMPLETED if success else DeploymentTarget.Status.FAILED

    with transaction.atomic():
        target.status = new_status
        target.completed_at = timezone.now()
        if error_log:
            target.error_log = error_log
        target.save(update_fields=["status", "completed_at", "error_log"])

        # Atomic counter increment — no race condition
        if success:
            Deployment.objects.filter(id=deployment_id).update(
                completed_devices=F("completed_devices") + 1
            )
        else:
            Deployment.objects.filter(id=deployment_id).update(
                failed_devices=F("failed_devices") + 1
            )

    # Re-fetch to broadcast accurate state
    deployment = Deployment.objects.get(id=deployment_id)
    _publish_progress(deployment)

    # Check if failure threshold breached
    if not success and deployment.failure_rate > deployment.max_failure_percentage:
        logger.warning("Deployment %s: failure threshold breached (%.1f%%)", deployment_id, deployment.failure_rate)

    return {"status": "RECORDED", "target_id": target_id, "success": success}


# ───────────────────────────────────────────────────────────────────────────
# Monitoring — detect stuck waves
# ───────────────────────────────────────────────────────────────────────────

@shared_task(
    queue="default",
    name="apps.deployments.tasks.monitor_stuck_waves",
)
def monitor_stuck_waves() -> dict:
    """
    Periodically check for waves that have been IN_PROGRESS longer than
    WAVE_TIMEOUT_MINUTES.  Marks them as FAILED and notifies via Redis.

    Register in celery_app.py beat schedule to run every 10 minutes.
    """
    cutoff = timezone.now() - timezone.timedelta(minutes=WAVE_TIMEOUT_MINUTES)

    stuck_targets = DeploymentTarget.objects.filter(
        status=DeploymentTarget.Status.IN_PROGRESS,
        started_at__lt=cutoff,
    ).select_related("deployment", "device")

    if not stuck_targets.exists():
        return {"stuck": 0}

    stuck_by_deployment: dict = {}
    for t in stuck_targets:
        dep_id = str(t.deployment_id)
        stuck_by_deployment.setdefault(dep_id, []).append(t)

    from django.db.models import F

    total_stuck = 0
    for dep_id, targets in stuck_by_deployment.items():
        with transaction.atomic():
            for t in targets:
                t.status = DeploymentTarget.Status.FAILED
                t.error_log = f"Wave timed out after {WAVE_TIMEOUT_MINUTES} minutes"
                t.completed_at = timezone.now()
                t.save(update_fields=["status", "error_log", "completed_at"])
            # Atomically bump failed_devices counter for all stuck targets at once
            Deployment.objects.filter(id=dep_id).update(
                failed_devices=F("failed_devices") + len(targets)
            )
            total_stuck += len(targets)

        try:
            deployment = Deployment.objects.get(id=dep_id)
            RedisPublisher.publish_notification(
                "warning",
                f"Deployment '{deployment.name}': {len(targets)} device(s) stuck in wave "
                f"{targets[0].wave_number} — auto-marked as failed after {WAVE_TIMEOUT_MINUTES}min timeout."
            )
            _publish_progress(deployment)
        except Deployment.DoesNotExist:
            pass

    logger.warning("monitor_stuck_waves: marked %d stuck targets as failed", total_stuck)
    return {"stuck": total_stuck}


# ───────────────────────────────────────────────────────────────────────────
# Backward-compatible shim — keeps old call sites working
# ───────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, queue="critical", max_retries=3)
def execute_deployment(self, deployment_id: str):
    """
    Backward-compatible entry point.  Delegates to orchestrate_deployment.
    Kept so existing Deployment.objects.filter(...) → execute_deployment.delay()
    calls continue to work without a code change.
    """
    return orchestrate_deployment(deployment_id)


@shared_task
def cancel_deployment_task(deployment_id: str):
    try:
        deployment = Deployment.objects.get(id=deployment_id)
        if deployment.status not in [Deployment.Status.COMPLETED, Deployment.Status.FAILED]:
            deployment.status = Deployment.Status.CANCELLED
            deployment.save(update_fields=["status"])

            targets = DeploymentTarget.objects.filter(
                deployment=deployment,
                status__in=[DeploymentTarget.Status.QUEUED, DeploymentTarget.Status.IN_PROGRESS],
            )
            for t in targets:
                if t.status == DeploymentTarget.Status.IN_PROGRESS:
                    RedisPublisher.publish_agent_command(
                        str(t.device.id), "CANCEL_DEPLOYMENT", {"deployment_id": str(deployment_id)}
                    )
                t.status = DeploymentTarget.Status.SKIPPED
                t.save(update_fields=["status"])

            _publish_progress(deployment)
    except Deployment.DoesNotExist:
        pass


@shared_task
def run_preflight_checks(deployment_id: str):
    """Legacy — called from old task references. Runs preflight for all queued targets."""
    try:
        deployment = Deployment.objects.get(id=deployment_id)
        targets = DeploymentTarget.objects.filter(
            deployment=deployment, status=DeploymentTarget.Status.QUEUED
        ).select_related("device")
        request_id = f"preflight_{deployment_id}_{int(time.time())}"
        for t in targets:
            RedisPublisher.publish_agent_command(str(t.device.id), "HEALTH_CHECK", {"request_id": request_id})
        logger.info("Pre-flight checks requested for deployment %s", deployment_id)
    except Deployment.DoesNotExist:
        pass


@shared_task
def process_scheduled_deployments():
    now = timezone.now()
    scheduled = Deployment.objects.filter(status=Deployment.Status.SCHEDULED, scheduled_at__lte=now)
    for d in scheduled:
        with transaction.atomic():
            d.status = Deployment.Status.IN_PROGRESS
            d.started_at = now
            d.save(update_fields=["status", "started_at"])
        orchestrate_deployment.delay(str(d.id))
