import json
from django.conf import settings
import redis
import logging

logger = logging.getLogger(__name__)

class DashboardCache:
    """Wrapper for handling UI cache calls efficiently without flooding the DB."""
    
    STATS_KEY = "dashboard:stats"
    COMPLIANCE_KEY = "dashboard:compliance"
    
    _client = None

    @classmethod
    def get_client(cls):
        if cls._client is None:
            redis_url = getattr(settings, 'CELERY_BROKER_URL', 'redis://localhost:6379/0')
            cls._client = redis.Redis.from_url(redis_url, decode_responses=True)
        return cls._client

    @classmethod
    def set_stats(cls, stats_dict: dict, ttl_seconds: int = 300):
        try:
            cls.get_client().setex(cls.STATS_KEY, ttl_seconds, json.dumps(stats_dict))
        except Exception as e:
            logger.error(f"Failed to cache dashboard stats: {e}")

    @classmethod
    def get_stats(cls) -> dict:
        try:
            data = cls.get_client().get(cls.STATS_KEY)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Failed to fetch dashboard stats: {e}")
            return None

    @classmethod
    def set_compliance_snapshot(cls, compliance_dict: dict, ttl_seconds: int = 86400):
        try:
            cls.get_client().setex(cls.COMPLIANCE_KEY, ttl_seconds, json.dumps(compliance_dict))
        except Exception as e:
            logger.error(f"Failed to cache compliance snapshot: {e}")

    @classmethod
    def get_compliance_snapshot(cls) -> dict:
        try:
            data = cls.get_client().get(cls.COMPLIANCE_KEY)
            return json.loads(data) if data else None
        except Exception:
            return None
