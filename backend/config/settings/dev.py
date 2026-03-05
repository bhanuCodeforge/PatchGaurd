from .base import *

# Security configuration for development
DEBUG = True
ALLOWED_HOSTS = ["*"]
CORS_ALLOW_ALL_ORIGINS = True

# Debug Toolbar configuration
if "debug_toolbar" not in INSTALLED_APPS:
    INSTALLED_APPS.insert(0, "debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Disable password validators in dev for easier testing
AUTH_PASSWORD_VALIDATORS = []

# Override REST framework defaults for development (e.g. adding browsable API back)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Email backend for dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery worker doesn't run in local dev — remove health check to avoid 500 on /api/health/
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "health_check.contrib.celery"]
