import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from auth import verify_ws_token, verify_agent_key
from ws_manager import manager
from agent_protocol import MessageEnvelope, ServerCommand

logger = logging.getLogger(__name__)

router = APIRouter()

# Pseudo-dependency function to attach DB pool from App State securely.
def get_db_pool():
    # Will be patched by main_loop
    pass

@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, token: str = Query(...)):
    try:
        user_data = await verify_ws_token(token)
        user_id = str(user_data.get("user_id", "anonymous"))
    except Exception as e:
        await websocket.close(code=1008, reason="Invalid Token")
        return

    await manager.connect_dashboard(websocket, user_id)
    try:
        while True:
            # Dashboard can send commands, e.g., Subscribe to deployment
            data = await websocket.receive_text()
            try:
                env = MessageEnvelope.model_validate_json(data)
                if env.event == "subscribe_deployment":
                    dep_id = env.payload.get("deployment_id")
                    if dep_id:
                        manager.subscribe_to_deployment(websocket, dep_id)
                        await websocket.send_json({"event": "subscribed", "payload": {"deployment_id": dep_id}})
                elif env.event == "unsubscribe_deployment":
                    dep_id = env.payload.get("deployment_id")
                    if dep_id:
                        manager.unsubscribe_from_deployment(websocket, dep_id)
            except Exception as e:
                logger.error(f"Error handling dashboard message: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id, is_agent=False)

@router.websocket("/ws/agent")
async def websocket_agent(websocket: WebSocket, api_key: str = Query(...)):
    # Retrieve DB pool from app state dynamically
    db_pool = websocket.app.state.pool
    
    device_id = await verify_agent_key(db_pool, api_key)
    if not device_id:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    await manager.connect_agent(websocket, device_id)
    try:
        while True:
            # Agents send heartbeats or command results
            data = await websocket.receive_text()
            try:
                env = MessageEnvelope.model_validate_json(data)
                # Redis queue updates (FastAPI direct DB updates or forward via Redis to Celery)
                # Typically, realtime service forwards these specific workloads to the backend message bus for Django / Celery scaling.
                from ws_manager import manager # ensure logic
            except Exception as e:
                logger.error(f"Error handling agent event: {e}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, device_id, is_agent=True)
