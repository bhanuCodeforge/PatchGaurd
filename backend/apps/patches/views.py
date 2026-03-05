from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
from apps.accounts.permissions import ReadOnlyForViewers, IsOperatorOrAbove, IsAdmin
from .models import Patch, DevicePatchStatus
from .filters import PatchFilter
from .serializers import (
    PatchListSerializer, PatchDetailSerializer, PatchCreateSerializer,
    PatchApprovalSerializer, DevicePatchStatusSerializer
)
from .state_machine import PatchStateMachine
from drf_spectacular.utils import extend_schema

class PatchViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyForViewers]
    filterset_class = PatchFilter
    search_fields = ["vendor_id", "title", "description", "cve_ids", "package_name"]
    ordering_fields = ["severity", "status", "released_at", "vendor"]
    queryset = Patch.objects.all().order_by('-released_at')

    def get_serializer_class(self):
        if self.action == 'list':
            return PatchListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return PatchCreateSerializer
        return PatchDetailSerializer

    @extend_schema(summary="Approve patch", description="Transition to approved state.", request=PatchApprovalSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def approve(self, request, pk=None):
        patch = self.get_object()
        serializer = PatchApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')
        
        try:
            PatchStateMachine.transition(patch, Patch.Status.APPROVED, user=request.user, reason=reason)
            return Response({"status": f"Patch {patch.vendor_id} approved."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Reject patch", description="Transition to rejected state.", request=PatchApprovalSerializer)
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def reject(self, request, pk=None):
        patch = self.get_object()
        serializer = PatchApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data.get('reason', '')
        
        try:
            PatchStateMachine.transition(patch, Patch.Status.REJECTED, user=request.user, reason=reason)
            return Response({"status": f"Patch {patch.vendor_id} rejected."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Review patch", description="Transition to reviewed state.")
    @action(detail=True, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def review(self, request, pk=None):
        patch = self.get_object()
        try:
            PatchStateMachine.transition(patch, Patch.Status.REVIEWED, user=request.user)
            return Response({"status": f"Patch {patch.vendor_id} marked as reviewed."})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(summary="Affected devices", description="List devices missing this patch.")
    @action(detail=True, methods=["get"])
    def affected_devices(self, request, pk=None):
        patch = self.get_object()
        statuses = DevicePatchStatus.objects.filter(patch=patch, state=DevicePatchStatus.State.MISSING).select_related('device')
        page = self.paginate_queryset(statuses)
        if page is not None:
            serializer = DevicePatchStatusSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = DevicePatchStatusSerializer(statuses, many=True)
        return Response(serializer.data)

    @extend_schema(summary="Bulk approve patches", description="Approve multiple patches at once.")
    @action(detail=False, methods=["post"], permission_classes=[IsOperatorOrAbove])
    def bulk_approve(self, request):
        patch_ids = request.data.get('patch_ids', [])
        patches = Patch.objects.filter(id__in=patch_ids)
        approved_count = 0
        errors = []
        for patch in patches:
            try:
                PatchStateMachine.transition(patch, Patch.Status.APPROVED, user=request.user, reason="Bulk approval")
                approved_count += 1
            except ValueError as e:
                errors.append(f"{patch.vendor_id}: {str(e)}")
        
        return Response({
            "status": f"Approved {approved_count} patches.",
            "errors": errors
        })

    @extend_schema(summary="Patch statistics", description="Aggregate stats for the patch catalog.")
    @action(detail=False, methods=["get"])
    def stats(self, request):
        total = Patch.objects.count()
        by_severity = list(Patch.objects.values('severity').annotate(count=Count('id')))
        by_status = list(Patch.objects.values('status').annotate(count=Count('id')))
        awaiting_review = Patch.objects.filter(status=Patch.Status.IMPORTED).count()
        critical_pending = Patch.objects.filter(severity=Patch.Severity.CRITICAL, status__in=[Patch.Status.IMPORTED, Patch.Status.REVIEWED]).count()
        
        return Response({
            'total': total,
            'by_severity': by_severity,
            'by_status': by_status,
            'awaiting_review_count': awaiting_review,
            'critical_pending_count': critical_pending
        })

    @extend_schema(summary="Overall compliance summary", description="Overall compliance rate across all devices.")
    @action(detail=False, methods=["get"])
    def compliance_summary(self, request):
        total_statuses = DevicePatchStatus.objects.count()
        installed = DevicePatchStatus.objects.filter(state=DevicePatchStatus.State.INSTALLED).count()
        missing = DevicePatchStatus.objects.filter(state=DevicePatchStatus.State.MISSING).count()
        
        compliance_rate = (installed / total_statuses * 100) if total_statuses > 0 else 100.0
        
        return Response({
            "overall_compliance_rate": round(compliance_rate, 2),
            "total_assessments": total_statuses,
            "installed_count": installed,
            "missing_count": missing
        })

class DevicePatchStatusViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [ReadOnlyForViewers]
    queryset = DevicePatchStatus.objects.all().select_related('device', 'patch').order_by('-last_attempt', 'id')
    serializer_class = DevicePatchStatusSerializer
    filterset_fields = ['state', 'device', 'patch']
