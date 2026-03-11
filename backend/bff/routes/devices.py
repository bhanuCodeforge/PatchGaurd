"""
BFF Routes — proxied /api/v1/devices with Redis caching.

Device list calls are expensive (large result sets, complex DB joins).
The BFF caches the full paginated JSON response and forwards cache
invalidation when write operations are performed.
"""
import logging
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
from bff.auth import require_auth, build_upstream_headers
from bff.cache import cache_get, cache_set, cache_delete, is_rate_limited
from bff.proxy import proxy_get, proxy_request
from bff.config import BFF_CACHE_TTL, RATE_LIMIT_DEVICES

logger = logging.getLogger(__name__)
router = APIRouter()

DEVICE_LIST_CACHE_PREFIX = "bff:devices:"


def _device_list_key(query_string: str, user_hint: str) -> str:
    """Cache key includes the full query string to handle pagination/filtering."""
    import hashlib
    qs_hash = hashlib.md5((query_string or "").encode()).hexdigest()[:12]
    return f"{DEVICE_LIST_CACHE_PREFIX}{user_hint}:{qs_hash}"


def _user_hint(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    try:
        import base64, json
        token = auth.split(" ", 1)[1] if " " in auth else auth
        padded = token.split(".")[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        return str(payload.get("user_id", "anon"))
    except Exception:
        return "anon"


@router.get("/api/v1/devices/")
@router.get("/api/v1/devices")
async def proxy_device_list(
    request: Request,
    _auth: str = Depends(require_auth),
):
    """
    Proxy + cache the device list endpoint.

    Rate-limited to RATE_LIMIT_DEVICES req/min per client IP.
    Cached for BFF_CACHE_TTL seconds per (user, query-string) combination.
    """
    client_ip = request.client.host if request.client else "unknown"
    if await is_rate_limited(f"{client_ip}:devices", RATE_LIMIT_DEVICES):
        raise HTTPException(status_code=429, detail="Too many requests.")

    user_hint = _user_hint(request)
    cache_key = _device_list_key(str(request.query_params), user_hint)

    cached = await cache_get(cache_key)
    if cached is not None:
        return JSONResponse(content=cached, headers={"X-BFF-Cache": "HIT"})

    data = await proxy_get("/api/v1/devices/", request, params=dict(request.query_params))
    await cache_set(cache_key, data, BFF_CACHE_TTL)
    return JSONResponse(content=data, headers={"X-BFF-Cache": "MISS"})


@router.api_route(
    "/api/v1/devices/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
)
async def proxy_device_detail(
    path: str,
    request: Request,
    _auth: str = Depends(require_auth),
):
    """
    Proxy all other device sub-paths verbatim.
    On write operations (POST/PUT/PATCH/DELETE) invalidate the device list cache.
    """
    upstream_path = f"/api/v1/devices/{path}"
    method = request.method.upper()
    body = await request.body() if method in ("POST", "PUT", "PATCH") else None

    resp = await proxy_request(method, upstream_path, request, body=body, params=dict(request.query_params))

    # Invalidate device list cache on writes
    if method in ("POST", "PUT", "PATCH", "DELETE") and resp.status_code < 300:
        user_hint = _user_hint(request)
        # Delete all cached pages for this user (pattern delete via scan)
        try:
            from bff.cache import get_redis
            r = await get_redis()
            pattern = f"{DEVICE_LIST_CACHE_PREFIX}{user_hint}:*"
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)
        except Exception as exc:
            logger.warning("Cache invalidation failed: %s", exc)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
    )
