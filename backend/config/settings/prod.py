from .base import *
import os

DEBUG = False

# Security settings
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "").split(",") if h]
CORS_ALLOWED_ORIGINS = [o for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o]

# HTTPS / TLS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000 # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SAMESITE = "Lax"

# Security Headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Force JSON logging for prod
LOGGING["loggers"]["patchguard"]["handlers"] = ["file", "console"]
LOGGING["loggers"]["django"]["handlers"] = ["console"]
LOGGING["formatters"]["console"]["()"] = "structlog.stdlib.ProcessorFormatter"
LOGGING["formatters"]["console"]["processor"] = "structlog.processors.JSONRenderer"
