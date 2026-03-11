import jwt
import os
from fastapi import HTTPException, status
from typing import Optional

SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("DJANGO_SECRET_KEY", "test"))
ALGORITHM = "HS256"

# A basic async PG connection pool will be passed to verify agents.
# For simplicity and isolation, we read from the DB without hitting Django ORM.

async def verify_jwt(token: str) -> dict:
    """Verifies standard DRF SimpleJWT token sent from dashboard."""
    try:
        # Check standard claim structure expected by SimpleJWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

async def verify_ws_token(token: str) -> dict:
    """"Verifies token passed via WS query params."""
    if not token:
         raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API Key or Token")
    return await verify_jwt(token)

async def verify_agent_key(db_pool, api_key: str) -> Optional[str]:
    """Look up an agent's device ID by matching Api Key.
    
    Strategy:
    - Prefer asyncpg direct DB query (when PostgreSQL pool is available)
    - Fallback: HTTP call to Django backend (SQLite / dev mode)
    """
    import logging
    _log = logging.getLogger(__name__)

    # Primary: direct DB (PostgreSQL)
    if db_pool is not None:
        try:
            async with db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM device WHERE agent_api_key = $1 AND status != 'decommissioned'",
                    api_key
                )
                if row:
                    return str(row['id'])
            return None
        except Exception as e:
            _log.error(f"DB auth error: {e} — falling back to REST auth")

    # Fallback: call Django REST API (works with SQLite in dev)
    try:
        import aiohttp
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{backend_url}/devices/",
                headers={"X-Agent-API-Key": api_key},
                params={"page_size": 1},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    # The key validated — now find the specific device
                    # Use a dedicated auth endpoint if available
                    pass
        # Try dedicated device lookup via agent-key header
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{backend_url}/devices/me/",
                headers={"X-Agent-API-Key": api_key},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    device_id = data.get("id")
                    if device_id:
                        _log.info(f"REST fallback auth succeeded for device {device_id}")
                        return str(device_id)
    except Exception as e:
        _log.error(f"REST fallback auth error: {e}")

    _log.warning("verify_agent_key: all auth methods failed — rejecting agent connection.")
    return None
