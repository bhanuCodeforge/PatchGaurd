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
    """Look up an agent's device ID by matching Api Key directly via asyncpg."""
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM inventory_device WHERE agent_api_key = $1 AND status != 'decommissioned'",
                api_key
            )
            if row:
                return str(row['id'])
    except Exception as e:
        import logging
        logging.error(f"Error authenticating API key: {e}")
    return None
