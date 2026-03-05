import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load .env from repo root (two levels above backend/)
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

INSTALLED_APPS = [
    # Default Django apps
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",

    # Third-party apps
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
    "drf_spectacular",
    "health_check",
    "health_check.db",
    "health_check.cache",
    "health_check.contrib.celery",
    "health_check.contrib.redis",

    # Local apps
    "apps.accounts",
    "apps.inventory",
    "apps.patches",
    "apps.deployments",
]

AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "common.middleware.AuditLogMiddleware",
    "common.middleware.RequestTimingMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Database
import dj_database_url

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "vector_db"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", "password"),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

# Optional: Log the name of the database being used to verify the fix
# print(f"DEBUG: Using database {DATABASES['default']['NAME']}")

if os.getenv("POSTGRES_READ_HOST"):
    DATABASES["readonly"] = dj_database_url.config(
        default=os.getenv("DATABASE_READ_URL")
    )
    DATABASE_ROUTERS = ["common.db_router.ReadReplicaRouter"]

# Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv("REDIS_CACHE_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
            "SOCKET_TIMEOUT": 5,
            "SOCKET_CONNECT_TIMEOUT": 5,
            "IGNORE_EXCEPTIONS": True,
        },
        "KEY_PREFIX": "pm",
        "TIMEOUT": 300,
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "common.pagination.StandardCursorPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle"
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "20/min",
        "user": "200/min"
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "common.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# Simple JWT
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_LIFETIME_MINUTES", 30))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_LIFETIME_DAYS", 7))),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": os.getenv("JWT_SECRET_KEY"),
    "TOKEN_OBTAIN_SERIALIZER": "apps.accounts.serializers.CustomTokenObtainSerializer",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Spectacular Setup
SPECTACULAR_SETTINGS = {
    "TITLE": "PatchGuard API",
    "DESCRIPTION": "Enterprise Patch Management System. WebSocket API available at ws://<host>/ws/ \n\nWebSocket Protocol: Connect to endpoints with JWT token and listen to dynamic event broadcast messages (Deployments, Discovery, Auth signals).",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "DeviceEnvironmentEnum": "apps.inventory.models.Device.Environment",
        "DeviceOSFamilyEnum": "apps.inventory.models.Device.OSFamily",
        "DeviceStatusEnum": "apps.inventory.models.Device.Status",
        "PatchSeverityEnum": "apps.patches.models.Patch.Severity",
        "PatchStatusEnum": "apps.patches.models.Patch.Status",
        "DevicePatchStateEnum": "apps.patches.models.DevicePatchStatus.State",
    },
    "CONTACT": {
        "name": "Dev Team",
        "email": "dev@patchguard.internal"
    },
    "LICENSE": {
        "name": "Proprietary"
    },
    "TAGS": [
        {"name": "Auth", "description": "Authentication and JWT endpoints"},
        {"name": "Users", "description": "User operations"},
        {"name": "Devices", "description": "Inventory and device groups"},
        {"name": "Patches", "description": "Patch catalog and workflows"},
        {"name": "Deployments", "description": "Deployment orchestration"},
        {"name": "Reports", "description": "Compliance and audit reports"},
        {"name": "Health", "description": "System health"},
    ],
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = "django-db"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 3600 # 1 hour hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 3300 # 55 min soft limit
CELERY_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_QUEUES = {
    "critical": {"exchange": "critical", "routing_key": "critical"},
    "default": {"exchange": "default", "routing_key": "default"},
    "reporting": {"exchange": "reporting", "routing_key": "reporting"},
}

# Logging Structure
import structlog
_log_dir = os.getenv("LOG_DIR", "/var/log/patchmgr")
os.makedirs(_log_dir, exist_ok=True)
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
        },
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "console",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(os.getenv("LOG_DIR", "/var/log/patchmgr"), "django.log"),
            "maxBytes": 1024 * 1024 * 50, # 50 MB
            "backupCount": 10,
            "formatter": "json",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "patchguard": {
            "handlers": ["console", "file"] if os.getenv("DJANGO_ENV") == "prod" else ["console"],
            "level": os.getenv("DJANGO_LOG_LEVEL", "INFO"),
        },
    },
}
# LDAP Settings
LDAP_SYNC_ENABLED = os.getenv('LDAP_SYNC_ENABLED', 'False') == 'True'
LDAP_URI = os.getenv('LDAP_URI', 'ldap://localhost:389')
LDAP_BIND_DN_TEMPLATE = os.getenv('LDAP_BIND_DN_TEMPLATE', 'uid=%s,ou=users,dc=example,dc=com')
LDAP_SEARCH_BASE = os.getenv('LDAP_SEARCH_BASE', 'dc=example,dc=com')
LDAP_ADMIN_GROUP = os.getenv('LDAP_ADMIN_GROUP', 'PatchMgr-Admins')
LDAP_OPERATOR_GROUP = os.getenv('LDAP_OPERATOR_GROUP', 'PatchMgr-Operators')

AUTHENTICATION_BACKENDS = [
    "apps.accounts.ldap_backend.LDAPBackend",
    "django.contrib.auth.backends.ModelBackend",
]
