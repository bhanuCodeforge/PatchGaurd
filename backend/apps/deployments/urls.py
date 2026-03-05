from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeploymentViewSet, DashboardStatsView, ComplianceReportView

router = DefaultRouter()
router.register(r'deployments', DeploymentViewSet, basename='deployment')

urlpatterns = [
    # Top level router for deployments
    path('', include(router.urls)),
    
    # Reports section
    path('reports/dashboard-stats/', DashboardStatsView.as_view(), name='dashboard-stats'),
    path('reports/compliance/', ComplianceReportView.as_view(), name='compliance-report'),
]
