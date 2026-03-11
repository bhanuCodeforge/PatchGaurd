"""
PatchGuard BFF — FastAPI application entry point.

Run with:
  cd backend
  uvicorn bff.main:app --host 0.0.0.0 --port 8080 --reload

Or via the Makefile:
  make bff-run
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from bff.proxy import init_http_client, close_http_client
from bff.routes import (
    dashboard_router,
    devices_router,
    api_proxy_router,
    ws_proxy_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise shared resources on startup, clean up on shutdown."""
    logger.info("BFF starting up — initialising HTTP client…")
    await init_http_client()
    yield
    logger.info("BFF shutting down — closing HTTP client…")
    await close_http_client()


app = FastAPI(
    title="PatchGuard BFF",
    description=(
        "Backend-for-Frontend gateway.  Angular connects exclusively here "
        "and the BFF forwards requests to Django (port 8000) and the realtime "
        "service (port 8001).  Single base URL for the entire API surface."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/bff/docs",
    redoc_url="/bff/redoc",
    openapi_url="/bff/openapi.json",
)

# ---------------------------------------------------------------------------
# CORS — mirror Django's settings for local dev
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/bff/health", tags=["BFF"])
async def health():
    return JSONResponse({"status": "ok", "service": "patchguard-bff"})


# ---------------------------------------------------------------------------
# Route registration (order matters — specific before catch-all)
# ---------------------------------------------------------------------------
app.include_router(dashboard_router, tags=["Dashboard"])
app.include_router(devices_router, tags=["Devices"])
app.include_router(ws_proxy_router, tags=["WebSocket"])
# Generic catch-all MUST be last
app.include_router(api_proxy_router, tags=["API Proxy"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("bff.main:app", host="0.0.0.0", port=8080, reload=True)
