"""
Generic HTTP proxy helpers for the BFF.

All upstream calls to Django go through here so error handling,
auth forwarding and timeout enforcement are consistent.
"""
import logging
import httpx
from fastapi import Request, HTTPException, status
from bff.config import BACKEND_URL, HTTP_TIMEOUT
from bff.auth import build_upstream_headers

logger = logging.getLogger(__name__)

# Shared async HTTP client — created once at startup via lifespan
_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialised — check BFF lifespan setup.")
    return _client


async def init_http_client() -> None:
    global _client
    _client = httpx.AsyncClient(
        base_url=BACKEND_URL,
        timeout=httpx.Timeout(HTTP_TIMEOUT),
        follow_redirects=True,
    )


async def close_http_client() -> None:
    global _client
    if _client:
        await _client.aclose()
        _client = None


# ---------------------------------------------------------------------------
# Proxy helpers
# ---------------------------------------------------------------------------

async def proxy_get(
    path: str,
    request: Request,
    *,
    params: dict | None = None,
) -> dict | list:
    """
    Forward a GET to the Django backend and return the parsed JSON body.
    Raises HTTP 502 on upstream errors, 504 on timeouts.
    """
    headers = build_upstream_headers(request)
    client = get_http_client()
    try:
        resp = await client.get(path, headers=headers, params=params)
        _raise_for_upstream(resp)
        return resp.json()
    except httpx.TimeoutException:
        logger.error("Upstream timeout on GET %s", path)
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Upstream timeout")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Upstream error on GET %s: %s", path, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream error")


async def proxy_request(
    method: str,
    path: str,
    request: Request,
    body: bytes | None = None,
    params: dict | None = None,
) -> httpx.Response:
    """
    Forward any HTTP method to the Django backend and return the raw httpx.Response.
    Caller is responsible for extracting content.
    """
    headers = build_upstream_headers(request)
    client = get_http_client()
    try:
        resp = await client.request(
            method,
            path,
            headers=headers,
            content=body,
            params=params,
        )
        return resp
    except httpx.TimeoutException:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Upstream timeout")
    except Exception as exc:
        logger.error("Upstream error on %s %s: %s", method, path, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Upstream error")


def _raise_for_upstream(resp: httpx.Response) -> None:
    """Translate upstream 4xx/5xx into BFF HTTP exceptions with correct codes."""
    if resp.status_code < 400:
        return
    # Pass through auth errors unchanged so Angular can redirect to login
    if resp.status_code in (401, 403):
        raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])
    if resp.status_code == 404:
        raise HTTPException(status_code=404, detail="Upstream resource not found")
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Upstream returned {resp.status_code}",
    )
