import json
import logging
import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth import verify_ws_token, verify_agent_key
from ws_manager import manager
from agent_protocol import MessageEnvelope, ServerCommand

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket, token: str = Query(...)):
    try:
        user_data = await verify_ws_token(token)
        user_id = str(user_data.get("user_id", "anonymous"))
    except Exception as e:
        logger.warning(f"Dashboard WS auth failed: {e}")
        await websocket.close(code=1008, reason="Invalid Token")
        return

    await manager.connect_dashboard(websocket, user_id)
    try:
        while True:
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
    # Verify API key against DB and resolve device_id
    db_pool = websocket.app.state.pool

    device_id = await verify_agent_key(db_pool, api_key)
    if not device_id:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    # Register agent by device_id (fixes the api_key vs device_id mismatch)
    await manager.connect_agent(websocket, device_id)

    # Notify all dashboards that an agent came online
    await manager.broadcast_to_dashboard(json.dumps({
        "event": "agent_online",
        "payload": {"device_id": device_id}
    }))

    try:
        while True:
            data = await websocket.receive_text()
            try:
                env = MessageEnvelope.model_validate_json(data)

                if env.event == "heartbeat":
                    # Forward heartbeat to all dashboard subscribers
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "agent_heartbeat",
                        "payload": {**env.payload, "device_id": device_id}
                    }))

                elif env.event == "system_info":
                    # Forward system info to all dashboards
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "agent_system_info",
                        "payload": {**env.payload, "device_id": device_id}
                    }))

                elif env.event in ("scan_results", "patch_result", "pong"):
                    # Forward agent responses to dashboards
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": env.event,
                        "payload": {**env.payload, "device_id": device_id}
                    }))

            except Exception as e:
                logger.error(f"Error handling agent event from {device_id}: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, device_id, is_agent=True)
        # Notify dashboards agent went offline
        await manager.broadcast_to_dashboard(json.dumps({
            "event": "agent_offline",
            "payload": {"device_id": device_id}
        }))
