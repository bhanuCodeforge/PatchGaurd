from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PatchViewSet, DevicePatchStatusViewSet

router = DefaultRouter()
router.register(r'status', DevicePatchStatusViewSet, basename='devicepatchstatus')
router.register(r'', PatchViewSet, basename='patch')

urlpatterns = [
    path('', include(router.urls)),
]
