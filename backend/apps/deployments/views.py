from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.utils import timezone
from apps.accounts.permissions import ReadOnlyForViewers, IsOperatorOrAbove, IsAdmin, IsAgentOrOperatorOrAbove
from common.agent_auth import AgentAPIKeyAuthentication
from .models import Deployment, DeploymentTarget
from .serializers import (
    DeploymentListSerializer, DeploymentDetailSerializer,
    DeploymentCreateSerializer, DeploymentTargetSerializer
)
from drf_spectacular.utils import extend_schema

from .filters import DeploymentFilter

_AGENT_AUTH = [AgentAPIKeyAuthentication, JWTAuthentication]

class DeploymentViewSet(viewsets.ModelViewSet):
    filterset_class = DeploymentFilter
    ordering_fields = ["created_at", "started_at", "status"]
    queryset = Deployment.objects.all().order_by('-created_at')

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAdmin()]
        elif self.action in ['create', 'update', 'partial_update', 'approve', 'execute', 'pause', 'resume', 'cancel', 'rollback']:
            return [IsOperatorOrAbove()]
        elif self.action == 'ingest_patch_result':
            return [IsAgentOrOperatorOrAbove()]
        return [ReadOnlyForViewers()]

    def get_serializer_class(self):
        if self.action == 'list':
            return DeploymentListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DeploymentCreateSerializer
        return DeploymentDetailSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deployment = self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        read_serializer = DeploymentDetailSerializer(deployment, context=self.get_serializer_context())
        return Response(read_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        target_device_ids = serializer.validated_data.pop('target_device_ids', None)
        deployment = serializer.save(created_by=self.request.user)

        # If frontend sent individual device IDs, create an ad-hoc group
        if target_device_ids:
            from apps.inventory.models import Device, DeviceGroup
            group = DeviceGroup.objects.create(
                name=f"_deploy_{deployment.id}",
                description=f"Auto-created group for deployment '{deployment.name}'",
            )
            devices = Device.objects.filter(id__in=target_device_ids)
            for dev in devices:
                dev.groups.add(group)
            deployment.target_groups.add(group)

        return deployment

    @extend_schema(summary="Approve deployment")
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        deployment = self.get_object()
        if deployment.status != Deployment.Status.DRAFT:
            return Response({"error": "Only draft deployments can be approved."}, status=status.HTTP_400_BAD_REQUEST)
        
        deployment.status = Deployment.Status.SCHEDULED
        deployment.approved_by = request.user
        deployment.save()
        return Response({"status": "Deployment approved and scheduled."})

    @extend_schema(summary="Execute deployment immediately")
    @action(detail=True, methods=["post"])
    def execute(self, request, pk=None):
        deployment = self.get_object()
        if deployment.status not in [Deployment.Status.SCHEDULED, Deployment.Status.DRAFT]:
            return Response({"error": "Cannot execute deployment in current state."}, status=status.HTTP_400_BAD_REQUEST)
        
        deployment.status = Deployment.Status.IN_PROGRESS
        deployment.started_at = timezone.now()
        deployment.save()

        from .tasks import execute_deployment
        execute_deployment.delay(str(deployment.id))
        return Response({"status": "Deployment execution started."})

    @extend_schema(summary="Pause deployment")
    @action(detail=True, methods=["post"])
    def pause(self, request, pk=None):
        deployment = self.get_object()
        if deployment.status != Deployment.Status.IN_PROGRESS:
            return Response({"error": "Only in-progress deployments can be paused."}, status=status.HTTP_400_BAD_REQUEST)
        
        deployment.status = Deployment.Status.PAUSED
        deployment.save()
        return Response({"status": "Deployment paused."})

    @extend_schema(summary="Resume deployment")
    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        deployment = self.get_object()
        if deployment.status != Deployment.Status.PAUSED:
            return Response({"error": "Only paused deployments can be resumed."}, status=status.HTTP_400_BAD_REQUEST)
        
        deployment.status = Deployment.Status.IN_PROGRESS
        deployment.save()
        return Response({"status": "Deployment resumed."})

    @extend_schema(summary="Cancel deployment")
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        deployment = self.get_object()
        if deployment.status in [Deployment.Status.COMPLETED, Deployment.Status.FAILED, Deployment.Status.CANCELLED, Deployment.Status.ROLLING_BACK]:
            return Response({"error": "Terminal deployments cannot be canceled."}, status=status.HTTP_400_BAD_REQUEST)

        from .tasks import cancel_deployment_task
        cancel_deployment_task.delay(str(deployment.id))
        return Response({"status": "Deployment canceled."})

    @extend_schema(summary="Rollback deployment")
    @action(detail=True, methods=["post"])
    def rollback(self, request, pk=None):
        deployment = self.get_object()
        if deployment.status not in [Deployment.Status.COMPLETED, Deployment.Status.FAILED]:
            return Response({"error": "Only completed or failed deployments can be rolled back."}, status=status.HTTP_400_BAD_REQUEST)

        deployment.status = Deployment.Status.ROLLING_BACK
        deployment.save()
        return Response({"status": "Deployment rollback initiated."})

    @extend_schema(
        summary="Ingest patch result from agent",
        description="Called by realtime service after agent reports patch_result. Updates DeploymentTarget status and advances deployment when all targets are complete.",
    )
    @action(
        detail=True, methods=["post"],
        authentication_classes=_AGENT_AUTH,
        permission_classes=[IsAgentOrOperatorOrAbove],
        url_path="ingest_patch_result",
    )
    def ingest_patch_result(self, request, pk=None):
        deployment = self.get_object()
        target_id = request.data.get("target_id")
        result_status = request.data.get("status")  # "completed" or "failed"
        error = request.data.get("error", "")

        if not target_id:
            return Response({"error": "target_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            target = DeploymentTarget.objects.get(id=target_id, deployment=deployment)
        except DeploymentTarget.DoesNotExist:
            return Response({"error": "Target not found"}, status=status.HTTP_404_NOT_FOUND)

        if target.status in (DeploymentTarget.Status.COMPLETED, DeploymentTarget.Status.FAILED):
            return Response({"status": "already finalized", "target_id": target_id})

        if result_status == "completed":
            target.status = DeploymentTarget.Status.COMPLETED
        else:
            target.status = DeploymentTarget.Status.FAILED
            target.error_log = error
        target.completed_at = timezone.now()
        target.save()

        from .tasks import update_deployment_counters, publish_progress
        update_deployment_counters(deployment)
        deployment.refresh_from_db()
        publish_progress(deployment)

        # Mark deployment complete/failed when all targets are finalized
        pending = DeploymentTarget.objects.filter(
            deployment=deployment,
            status__in=[DeploymentTarget.Status.QUEUED, DeploymentTarget.Status.IN_PROGRESS],
        ).exists()
        if not pending and deployment.status == Deployment.Status.IN_PROGRESS:
            if deployment.failure_rate > deployment.max_failure_percentage:
                deployment.status = Deployment.Status.FAILED
            else:
                deployment.status = Deployment.Status.COMPLETED
            deployment.completed_at = timezone.now()
            deployment.save(update_fields=["status", "completed_at"])
            publish_progress(deployment)

        return Response({"status": "patch result ingested", "target_id": target_id})

    @extend_schema(summary="Get progress targets", responses=DeploymentTargetSerializer(many=True))
    @action(detail=True, methods=["get"])
    def targets(self, request, pk=None):
        deployment = self.get_object()
        targets = DeploymentTarget.objects.filter(deployment=deployment).select_related('device')
        page = self.paginate_queryset(targets)
        if page is not None:
            serializer = DeploymentTargetSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DeploymentTargetSerializer(targets, many=True)
        return Response(serializer.data)

from rest_framework.views import APIView

class DashboardStatsView(APIView):
    permission_classes = [ReadOnlyForViewers]
    @extend_schema(summary="Dashboard Stats", description="Global reporting stats for dashboard caching.")
    def get(self, request):
        from apps.inventory.models import Device
        from apps.patches.models import Patch, DevicePatchStatus
        from django.db.models import Count

        total_devices = Device.objects.count()
        online_devices = Device.objects.filter(status=Device.Status.ONLINE).count()

        # Compliance: devices with ALL applicable patches installed
        # Simplified: count MISSING patch statuses vs total
        total_statuses = DevicePatchStatus.objects.count()
        missing = DevicePatchStatus.objects.filter(state=DevicePatchStatus.State.MISSING).count()
        compliance_rate = round(((total_statuses - missing) / total_statuses * 100), 1) if total_statuses else 100.0

        # OS breakdown
        by_os = {
            row["os_family"]: row["count"]
            for row in Device.objects.values("os_family").annotate(count=Count("id"))
        }

        return Response({
            "total_devices": total_devices,
            "online_devices": online_devices,
            "active_deployments": Deployment.objects.filter(status__in=[Deployment.Status.SCHEDULED, Deployment.Status.IN_PROGRESS]).count(),
            "pending_patches": Patch.objects.filter(status=Patch.Status.IMPORTED).count(),
            "critical_patches": Patch.objects.filter(severity=Patch.Severity.CRITICAL, status__in=[Patch.Status.IMPORTED, Patch.Status.APPROVED]).count(),
            "compliance_rate": compliance_rate,
            "missing_patches": missing,
            "by_os": by_os,
            "offline_devices": Device.objects.filter(status=Device.Status.OFFLINE).count(),
            "maintenance_devices": Device.objects.filter(status=Device.Status.MAINTENANCE).count(),
        })

class ComplianceReportView(APIView):
    permission_classes = [ReadOnlyForViewers]
    @extend_schema(summary="Compliance Report", description="Detailed compliance report generation.")
    def get(self, request):
        from apps.inventory.models import Device
        from apps.patches.models import Patch, DevicePatchStatus
        from django.db.models import Count, Q, Avg
        
        total_devices = Device.objects.count()
        if total_devices == 0:
            return Response({"overall": 100, "compliant_devices": 0, "non_compliant_devices": 0, "total_devices": 0})
            
        # Overall Compliance Rate (Average of all device rates)
        overall = Device.objects.aggregate(avg=Avg('compliance_rate'))['avg'] or 0.0
        
        # Compliant Devices (Rate >= 90%)
        compliant_devices = Device.objects.filter(compliance_rate__gte=90).count()
        non_compliant_devices = total_devices - compliant_devices
        
        # Severity breakdown of MISSING patches
        missing_by_sev = DevicePatchStatus.objects.filter(
            state=DevicePatchStatus.State.MISSING
        ).values('patch__severity').annotate(count=Count('id'))
        
        sev_counts = {row['patch__severity']: row['count'] for row in missing_by_sev}
        total_missing = sum(sev_counts.values()) or 1
        
        return Response({
            "overall": round(overall, 1),
            "compliant_devices": compliant_devices,
            "non_compliant_devices": non_compliant_devices,
            "total_devices": total_devices,
            "critical_pct": round((sev_counts.get('critical', 0) / total_missing * 100), 1),
            "high_pct": round((sev_counts.get('high', 0) / total_missing * 100), 1),
            "medium_pct": round((sev_counts.get('medium', 0) / total_missing * 100), 1),
            "low_pct": round((sev_counts.get('low', 0) / total_missing * 100), 1),
        })
