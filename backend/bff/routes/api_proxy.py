"""
BFF Routes — generic pass-through proxy for all remaining /api/*  paths.

Everything not explicitly handled by dashboard.py or devices.py flows
through here, translated transparently to the Django backend.
"""
import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from bff.auth import require_auth
from bff.proxy import proxy_request

logger = logging.getLogger(__name__)
router = APIRouter()


@router.api_route(
    "/api/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def generic_api_proxy(
    path: str,
    request: Request,
    _auth: str = Depends(require_auth),
):
    """
    Catch-all proxy: forwards any /api/* request to the Django backend,
    including all headers and body, and returns the upstream response as-is.
    """
    upstream_path = f"/api/{path}"
    method = request.method.upper()
    body = await request.body() if method not in ("GET", "HEAD", "OPTIONS") else None

    resp = await proxy_request(
        method,
        upstream_path,
        request,
        body=body,
        params=dict(request.query_params),
    )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
        headers={
            k: v for k, v in resp.headers.items()
            if k.lower() not in ("content-encoding", "transfer-encoding", "connection")
        },
    )
