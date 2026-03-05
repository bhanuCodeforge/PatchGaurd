from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from apps.accounts.permissions import ReadOnlyForViewers, IsOperatorOrAbove, IsAdmin
from .models import Deployment, DeploymentTarget
from .serializers import (
    DeploymentListSerializer, DeploymentDetailSerializer, 
    DeploymentCreateSerializer, DeploymentTargetSerializer
)
from drf_spectacular.utils import extend_schema

from .filters import DeploymentFilter

class DeploymentViewSet(viewsets.ModelViewSet):
    filterset_class = DeploymentFilter
    ordering_fields = ["created_at", "started_at", "status"]
    queryset = Deployment.objects.all().order_by('-created_at')

    def get_permissions(self):
        if self.action in ['destroy']:
            return [IsAdmin()]
        elif self.action in ['create', 'update', 'partial_update', 'approve', 'execute', 'pause', 'resume', 'cancel', 'rollback']:
            return [IsOperatorOrAbove()]
        return [ReadOnlyForViewers()]

    def get_serializer_class(self):
        if self.action == 'list':
            return DeploymentListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return DeploymentCreateSerializer
        return DeploymentDetailSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

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
        from apps.patches.models import Patch
        
        return Response({
            "total_devices": Device.objects.count(),
            "online_devices": Device.objects.filter(status=Device.Status.ONLINE).count(),
            "active_deployments": Deployment.objects.filter(status__in=[Deployment.Status.SCHEDULED, Deployment.Status.IN_PROGRESS]).count(),
            "pending_patches": Patch.objects.filter(status=Patch.Status.IMPORTED).count()
        })

class ComplianceReportView(APIView):
    permission_classes = [ReadOnlyForViewers]
    @extend_schema(summary="Compliance Report", description="Detailed compliance report generation.")
    def get(self, request):
        # A full implementation would query caching layer / snapshot tables
        return Response({"status": "Report rendering enabled", "data": []})
