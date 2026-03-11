from bff.routes.dashboard import router as dashboard_router
from bff.routes.devices import router as devices_router
from bff.routes.api_proxy import router as api_proxy_router
from bff.routes.ws_proxy import router as ws_proxy_router

__all__ = ["dashboard_router", "devices_router", "api_proxy_router", "ws_proxy_router"]
