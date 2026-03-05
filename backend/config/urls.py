from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
import health_check.urls

urlpatterns = [
    path("admin/", admin.site.urls),
    
    path('api/auth/', include('apps.accounts.urls')),
    path('api/v1/users/', include('apps.accounts.urls_users')),
    path('api/v1/devices/', include('apps.inventory.urls')),
    path('api/v1/patches/', include('apps.patches.urls')),
    path('api/v1/', include('apps.deployments.urls')),  # Includes reports/ AND deployments/
    
    # Swagger / DRF Spectacular config
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    
    # Health check
    path("api/health/", include(health_check.urls)),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
