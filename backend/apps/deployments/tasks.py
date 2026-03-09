from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.utils import timezone
from django.db import transaction
import math
import time
import logging

from .models import Deployment, DeploymentTarget
from common.redis_pubsub import RedisPublisher

logger = logging.getLogger(__name__)

def update_deployment_counters(deployment):
    targets = DeploymentTarget.objects.filter(deployment=deployment)
    total = targets.count()
    completed = targets.filter(status=DeploymentTarget.Status.COMPLETED).count()
    failed = targets.filter(status=DeploymentTarget.Status.FAILED).count()
    
    deployment.total_devices = total
    deployment.completed_devices = completed
    deployment.failed_devices = failed
    deployment.save(update_fields=['total_devices', 'completed_devices', 'failed_devices'])

def publish_progress(deployment):
    progress_data = {
        "status": deployment.status,
        "current_wave": deployment.current_wave,
        "progress_percentage": deployment.progress_percentage,
        "failure_rate": deployment.failure_rate
    }
    RedisPublisher.publish_deployment_progress(deployment.id, progress_data)

@shared_task(bind=True, queue="critical", max_retries=3)
def execute_deployment(self, deployment_id: str):
    logger.info(f"Starting execution of deployment {deployment_id}")
    
    try:
        deployment = Deployment.objects.get(id=deployment_id)
        
        if deployment.status != Deployment.Status.IN_PROGRESS:
            logger.warning(f"Deployment {deployment_id} is not IN_PROGRESS. Status: {deployment.status}")
            return "Deployment not active"

        # Initialize targets if not created yet (for simplicity we construct here)
        existing_targets = DeploymentTarget.objects.filter(deployment=deployment).exists()
        if not existing_targets:
            # Gather unique devices from target_groups
            device_ids = set()
            for group in deployment.target_groups.all():
                for dev in group.get_devices().values_list('id', flat=True):
                    device_ids.add(dev)
                    
            devices = list(device_ids)
            total = len(devices)
            
            # Construct Waves based on Strategy
            if total == 0:
                deployment.status = Deployment.Status.COMPLETED
                deployment.completed_at = timezone.now()
                deployment.save()
                return "No targets found"

            # Strategy: IMMEDIATE -> Wave 0 only
            # Strategy: ROLLOUT -> Batches
            # Strategy: CANARY -> Wave 0 is Canary%, Wave 1+ is normal
            wave_targets = []
            if deployment.strategy == Deployment.Strategy.IMMEDIATE:
                for d in devices:
                    wave_targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=0))
            elif deployment.strategy == Deployment.Strategy.CANARY:
                canary_count = max(1, int(total * (deployment.canary_percentage / 100)))
                canary_devices = devices[:canary_count]
                rest_devices = devices[canary_count:]
                for d in canary_devices:
                    wave_targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=0))
                
                # Further waves use wave_size
                wave_size = deployment.wave_size
                w = 1
                for i in range(0, len(rest_devices), wave_size):
                    for d in rest_devices[i:i+wave_size]:
                        wave_targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=w))
                    w += 1
            else:
                # Rolling
                wave_size = deployment.wave_size
                w = 0
                for i in range(0, total, wave_size):
                    for d in devices[i:i+wave_size]:
                        wave_targets.append(DeploymentTarget(deployment=deployment, device_id=d, wave_number=w))
                    w += 1
            
            DeploymentTarget.objects.bulk_create(wave_targets)
            update_deployment_counters(deployment)

        # Iterate over uncompleted waves
        waves = DeploymentTarget.objects.filter(deployment=deployment).values_list('wave_number', flat=True).distinct().order_by('wave_number')
        
        for w in waves:
            # Before starting wave check if paused/cancelled
            deployment.refresh_from_db()
            if deployment.status != Deployment.Status.IN_PROGRESS:
                logger.info(f"Deployment {deployment_id} halted. Status is {deployment.status}")
                return f"Halted at wave {w}"
                
            # Check failure threshold
            if deployment.failure_rate > deployment.max_failure_percentage:
                deployment.status = Deployment.Status.FAILED
                deployment.completed_at = timezone.now()
                deployment.save()
                RedisPublisher.publish_notification("error", f"Deployment {deployment.name} halted due to failure rate breaching threshold.")
                publish_progress(deployment)
                return "Failed Max Threshold"

            deployment.current_wave = w
            deployment.save(update_fields=['current_wave'])
            publish_progress(deployment)

            # Pre-flight Health Checks (Sec 7.6.2)
            run_preflight_checks(str(deployment_id))
            # Poll for health check results with timeout
            wave_targets = DeploymentTarget.objects.filter(
                deployment=deployment, wave_number=w, status=DeploymentTarget.Status.QUEUED
            ).select_related('device')
            preflight_deadline = timezone.now() + timezone.timedelta(seconds=60)
            while timezone.now() < preflight_deadline:
                all_reported = True
                for t in wave_targets:
                    t.device.refresh_from_db()
                    last_health = t.device.metadata.get('last_health_check') if t.device.metadata else None
                    if not last_health or last_health.get('timestamp', '') < str(timezone.now() - timezone.timedelta(seconds=90)):
                        all_reported = False
                        break
                if all_reported:
                    break
                time.sleep(3)

            # Evaluate preflight results — skip unhealthy devices
            for t in wave_targets:
                t.device.refresh_from_db()
                health = t.device.metadata.get('last_health_check', {}) if t.device.metadata else {}
                disk_free = health.get('disk_free_pct', 100)
                cpu_busy = health.get('cpu_pct', 0)
                mem_used = health.get('memory_pct', 0)
                if disk_free < 10 or cpu_busy > 95 or mem_used > 95:
                    t.status = DeploymentTarget.Status.SKIPPED
                    t.result_log = f"Preflight failed: disk={disk_free}%, cpu={cpu_busy}%, mem={mem_used}%"
                    t.completed_at = timezone.now()
                    t.save()
                    logger.warning(f"Skipping device {t.device.hostname} - preflight failed: {t.result_log}")
            update_deployment_counters(deployment)
            deployment.refresh_from_db()

            # Collect patch vendor IDs to send to agent
            patch_ids = list(deployment.patches.values_list('vendor_id', flat=True))

            targets = DeploymentTarget.objects.filter(deployment=deployment, wave_number=w, status=DeploymentTarget.Status.QUEUED)
            for t in targets:
                t.status = DeploymentTarget.Status.IN_PROGRESS
                t.started_at = timezone.now()
                t.save()
                # FIX: use device.id (UUID), not agent_api_key — realtime ws_manager
                # stores agents by device_id
                RedisPublisher.publish_agent_command(
                    str(t.device.id),
                    "START_DEPLOYMENT",
                    {
                        "deployment_id": str(deployment_id),
                        "target_id": str(t.id),
                        "patches": patch_ids,
                    },
                )

            # In a real app we'd spawn target polling tasks. For now, simulate asynchronous execution polling.
            logger.info(f"Deployed Wave {w}. Waiting for completion tracking via agent webhooks.")
            
            # Wave Delay Enforcement (1.0 Parity)
            # We only delay if there's another wave coming
            next_wave = waves.filter(wave_number__gt=w).first()
            if next_wave and deployment.strategy != Deployment.Strategy.IMMEDIATE:
                # FIX: wave_delay_minutes in model, let's use seconds for sleep
                delay_mins = deployment.wave_delay_minutes or 0
                delay_sec = max(30, delay_mins * 60) # Minimum 30s safety buffer
                logger.info(f"Enforcing wave delay of {delay_sec}s before proceeding to wave {next_wave}")
                time.sleep(delay_sec)
            
    except SoftTimeLimitExceeded:
        logger.warning(f"Time limit exceeded for deployment {deployment_id}")
        self.retry(countdown=60)
    except Exception as e:
        logger.error(f"Execution failed for {deployment_id}: {str(e)}")
        raise e

@shared_task
def cancel_deployment_task(deployment_id: str):
    try:
        deployment = Deployment.objects.get(id=deployment_id)
        if deployment.status not in [Deployment.Status.COMPLETED, Deployment.Status.FAILED]:
            deployment.status = Deployment.Status.CANCELLED
            deployment.save()
            
            targets = DeploymentTarget.objects.filter(deployment=deployment, status__in=[DeploymentTarget.Status.QUEUED, DeploymentTarget.Status.IN_PROGRESS])
            for t in targets:
                t.status = DeploymentTarget.Status.SKIPPED
                if t.status == DeploymentTarget.Status.IN_PROGRESS:
                    RedisPublisher.publish_agent_command(
                        str(t.device.id),  # FIX: was agent_api_key
                        "CANCEL_DEPLOYMENT",
                        {"deployment_id": str(deployment_id)},
                    )
                t.save()
            publish_progress(deployment)
    except Deployment.DoesNotExist:
        pass

@shared_task
def run_preflight_checks(deployment_id: str):
    """
    Command all target devices to report live health metrics.
    Updates targets to HEALTH_CHECK status.
    """
    try:
        deployment = Deployment.objects.get(id=deployment_id)
        targets = DeploymentTarget.objects.filter(
            deployment=deployment, 
            status=DeploymentTarget.Status.QUEUED
        ).select_related('device')
        
        request_id = f"preflight_{deployment_id}_{int(time.time())}"
        
        for t in targets:
            RedisPublisher.publish_agent_command(
                str(t.device.id),
                "HEALTH_CHECK",
                {"request_id": request_id}
            )
            
        logger.info(f"Pre-flight health checks requested for deployment {deployment_id}")
    except Deployment.DoesNotExist:
        pass

@shared_task
def process_scheduled_deployments():
    now = timezone.now()
    scheduled = Deployment.objects.filter(status=Deployment.Status.SCHEDULED, scheduled_at__lte=now)
    for d in scheduled:
        d.status = Deployment.Status.IN_PROGRESS
        d.started_at = now
        d.save()
        execute_deployment.delay(str(d.id))
