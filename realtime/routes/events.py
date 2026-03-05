from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict
from ws_manager import manager
from agent_protocol import ServerCommand

router = APIRouter()

class CommandPayload(BaseModel):
    command: str
    args: Dict[str, Any] = {}

@router.post("/rt/agents/{device_id}/command")
async def send_agent_command(device_id: str, payload: CommandPayload):
    # This route allows REST microservices (like Django) to force push an immediate agent WS command
    # However, standard practice flows through Redis pub/sub inside the main loop instead!
    success = await manager.send_to_agent(device_id, payload.model_dump_json())
    if not success:
        raise HTTPException(status_code=404, detail="Agent offline or disconnected")
    return {"status": "dispatched"}

@router.get("/rt/agents/online")
async def get_online_agents():
    return {"online_agents": manager.get_online_agents()}

@router.get("/rt/stats")
async def get_stats():
    return {
        "active_dashboard_connections": manager.get_dashboard_count(),
        "active_agent_connections": manager.get_agent_count(),
        "total_managed_sockets": manager.get_dashboard_count() + manager.get_agent_count()
    }
