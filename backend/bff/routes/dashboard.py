"""
BFF Routes — aggregated /api/v1/dashboard endpoint.

Calls three Django endpoints in parallel and merges the results into a
single response for the Angular dashboard page.  Results are cached in
Redis with a short TTL to absorb chatty polling from multiple open tabs.
"""
import asyncio
import logging
from fastapi import APIRouter, Request, Depends, HTTPException
from bff.auth import require_auth, build_upstream_headers
from bff.cache import cache_get, cache_set, is_rate_limited
from bff.proxy import proxy_get
from bff.config import DASHBOARD_CACHE_TTL, RATE_LIMIT_DASHBOARD

logger = logging.getLogger(__name__)
router = APIRouter()


def _dashboard_cache_key(user_id_hint: str) -> str:
    # Keyed per user so tenant data doesn't bleed across accounts
    return f"bff:dashboard:{user_id_hint}"


def _user_hint(request: Request) -> str:
    """Pull the user ID from JWT sub claim without full verification.
    Full verification happens inside Django — here we only need a
    cache-bucket discriminator."""
    auth = request.headers.get("Authorization", "")
    try:
        import base64, json
        token = auth.split(" ", 1)[1] if " " in auth else auth
        # Decode payload without verification (BFF trusts Django for real auth)
        padded = token.split(".")[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        return str(payload.get("user_id", "anon"))
    except Exception:
        return "anon"


@router.get("/api/v1/dashboard")
async def aggregated_dashboard(
    request: Request,
    _auth: str = Depends(require_auth),
):
    """
    Aggregate endpoint: merges stats from:
      GET /api/v1/devices/summary/      → device counts by status
      GET /api/v1/patches/compliance/   → overall compliance rate + breakdown
      GET /api/v1/deployments/recent/   → last 5 deployments

    Rate-limited to RATE_LIMIT_DASHBOARD req/min per client IP.
    Cached for DASHBOARD_CACHE_TTL seconds per user to handle multiple tabs.
    """
    client_ip = request.client.host if request.client else "unknown"
    rl_key = f"{client_ip}:dashboard"
    if await is_rate_limited(rl_key, RATE_LIMIT_DASHBOARD):
        raise HTTPException(status_code=429, detail="Too many requests — slow down polling.")

    user_hint = _user_hint(request)
    cache_key = _dashboard_cache_key(user_hint)

    cached = await cache_get(cache_key)
    if cached:
        return cached

    # Fan-out to three Django endpoints in parallel
    try:
        devices_task    = asyncio.create_task(proxy_get("/api/v1/devices/summary/", request))
        compliance_task = asyncio.create_task(proxy_get("/api/v1/patches/compliance/", request))
        deployments_task = asyncio.create_task(proxy_get("/api/v1/deployments/recent/", request))

        devices, compliance, deployments = await asyncio.gather(
            devices_task, compliance_task, deployments_task,
            return_exceptions=True,
        )
    except Exception as exc:
        logger.error("Dashboard aggregation error: %s", exc)
        raise HTTPException(status_code=502, detail="Dashboard aggregation failed")

    # Build merged payload — partial failures return a degraded response
    result: dict = {}

    if isinstance(devices, dict):
        result["devices"] = devices
    else:
        result["devices"] = None
        logger.warning("device summary upstream error: %s", devices)

    if isinstance(compliance, dict):
        result["compliance"] = compliance
    else:
        result["compliance"] = None
        logger.warning("compliance upstream error: %s", compliance)

    if isinstance(deployments, (dict, list)):
        result["recent_deployments"] = deployments
    else:
        result["recent_deployments"] = []
        logger.warning("deployments upstream error: %s", deployments)

    await cache_set(cache_key, result, DASHBOARD_CACHE_TTL)
    return result
