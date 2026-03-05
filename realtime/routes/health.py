from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "realtime_websocket_node"}

@router.get("/health/detailed")
async def detailed_health():
    # Placeholder for active connections tracking metrics.
    from ws_manager import manager
    return {
        "status": "ok", 
        "service": "realtime_websocket_node",
        "active_dashboard_clients": manager.get_dashboard_count(),
        "active_agent_clients": manager.get_agent_count()
    }
