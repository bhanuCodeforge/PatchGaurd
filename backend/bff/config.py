"""
BFF Configuration — loaded from environment variables.
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load from repo-root .env
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# Upstream service URLs
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://localhost:8000")
REALTIME_URL: str = os.getenv("REALTIME_URL", "http://localhost:8001")
REALTIME_WS_URL: str = os.getenv("REALTIME_WS_URL", "ws://localhost:8001")

# Redis for BFF caching (dedicated DB to avoid polluting app cache)
REDIS_URL: str = os.getenv("BFF_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/2"))

# Cache TTLs (seconds)
BFF_CACHE_TTL: int = int(os.getenv("BFF_CACHE_TTL", "30"))
DASHBOARD_CACHE_TTL: int = int(os.getenv("DASHBOARD_CACHE_TTL", "10"))

# Rate limits (requests per 60-second window, per client IP)
RATE_LIMIT_DEVICES: int = int(os.getenv("RATE_LIMIT_DEVICES", "60"))
RATE_LIMIT_DASHBOARD: int = int(os.getenv("RATE_LIMIT_DASHBOARD", "120"))

# HTTP client timeout (seconds for upstream requests)
HTTP_TIMEOUT: float = float(os.getenv("BFF_HTTP_TIMEOUT", "10.0"))
