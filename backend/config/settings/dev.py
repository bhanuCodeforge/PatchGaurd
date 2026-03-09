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

# Override REST framework defaults for development (browsable API)
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
    "rest_framework.renderers.JSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
)

# Email backend for dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Remove health checks that require external services in local dev
INSTALLED_APPS = [
    app for app in INSTALLED_APPS
    if app not in (
        "health_check.contrib.celery",
        "health_check.contrib.redis",
    )
]

# Use in-memory cache if Redis is not configured or unavailable
_redis_cache_url = os.getenv("REDIS_CACHE_URL", "")
if not _redis_cache_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "patchguard-dev",
        }
    }
else:
    # Keep Redis cache from base.py but suppress connection errors gracefully
    CACHES["default"]["OPTIONS"]["IGNORE_EXCEPTIONS"] = True

# Make Celery optional: if no broker set, use in-process eager execution
_celery_broker = os.getenv("CELERY_BROKER_URL", "")
if not _celery_broker:
    CELERY_TASK_ALWAYS_EAGER = True
    CELERY_TASK_EAGER_PROPAGATES = True

# Agent installer config: URLs written into the downloaded config.yaml
AGENT_REST_URL = os.getenv("AGENT_REST_URL", "http://localhost:8000/api/v1")
AGENT_WS_URL = os.getenv("AGENT_WS_URL", "ws://localhost:8001/ws/agent")
