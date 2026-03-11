from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SystemSettingViewSet

router = DefaultRouter()
router.register(r'', SystemSettingViewSet, basename='systemsetting')

urlpatterns = [
    path('', include(router.urls)),
]
