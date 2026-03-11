import secrets
from typing import Generator, Any, Optional, Callable, Dict
from django.core.cache import cache

def generate_api_key() -> str:
    """
    Generates a secure 64-character hex string for API keys.
    """
    return secrets.token_hex(32)

def get_client_ip(request) -> str:
    """
    Extracts the real client IP address from the request headers
    or falls back to the REMOTE_ADDR.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('HTTP_X_REAL_IP', request.META.get('REMOTE_ADDR', ''))
    return ip

def batch_qs(queryset, batch_size: int = 500) -> Generator[Any, None, None]:
    """
    A generator that yields a database queryset in manageable chunks.
    Useful for processing large datasets without exhausting memory.
    """
    total = queryset.count()
    for start in range(0, total, batch_size):
        end = min(start + batch_size, total)
        yield queryset[start:end]


class CacheHelper:
    """
    Utility methods for common caching patterns.
    """
    @staticmethod
    def get_or_set(key: str, callable_func: Callable[[], Any], timeout: int = 300) -> Any:
        result = cache.get(key)
        if result is None:
            result = callable_func()
            cache.set(key, result, timeout)
        return result

    @staticmethod
    def invalidate_pattern(pattern: str) -> None:
        """
        Deletes all keys matching a pattern. Warning: requires redis.
        """
        try:
            cache.delete_pattern(pattern)
        except AttributeError:
            # fallback if not using django-redis
            pass

    @staticmethod
    def cache_dashboard_stats(stats_dict: Dict[str, Any], timeout: int = 60) -> None:
        cache.set("dashboard:stats", stats_dict, timeout)

    @staticmethod
    def get_dashboard_stats() -> Optional[Dict[str, Any]]:
        return cache.get("dashboard:stats")
