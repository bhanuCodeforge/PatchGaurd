from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DeviceViewSet, DeviceGroupViewSet

router = DefaultRouter()
router.register(r'groups', DeviceGroupViewSet, basename='devicegroup')
router.register(r'', DeviceViewSet, basename='device')

urlpatterns = [
    path('', include(router.urls)),
]
