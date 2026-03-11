"""
Auth passthrough helpers for the BFF.

The BFF accepts the same JWT Bearer token the Angular client already has
and forwards it verbatim to upstream Django.  No token re-issuance occurs
here — the BFF is transparent on the auth path.

Supported schemes:
  1. Authorization: Bearer <jwt>     (primary — Angular)
  2. Cookie: access_token=<jwt>      (fallback — httpOnly cookie flow)
"""
from fastapi import Request, HTTPException, status


def extract_auth_header(request: Request) -> str | None:
    """
    Extract a raw Authorization header value from the incoming request.

    Returns the full 'Bearer <token>' string, or None if absent.
    Cookie-based tokens are promoted to an Authorization header for
    uniform forwarding to upstream services.
    """
    auth = request.headers.get("Authorization")
    if auth:
        return auth

    # Promote httpOnly cookie to header (cookie-based auth flow)
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return f"Bearer {cookie_token}"

    return None


def require_auth(request: Request) -> str:
    """
    Like extract_auth_header() but raises 401 if no credential is present.
    Use as a FastAPI dependency.
    """
    auth = extract_auth_header(request)
    if not auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth


def build_upstream_headers(request: Request) -> dict[str, str]:
    """
    Build the headers dict that should be forwarded to upstream Django.

    Forwards:
      - Authorization  (JWT Bearer)
      - X-Request-ID   (tracing — if present)
      - Content-Type   (if present)
    """
    headers: dict[str, str] = {}

    auth = extract_auth_header(request)
    if auth:
        headers["Authorization"] = auth

    for h in ("X-Request-ID", "Content-Type", "Accept-Language"):
        val = request.headers.get(h)
        if val:
            headers[h] = val

    return headers
