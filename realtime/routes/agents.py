import json
import logging
import asyncio
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth import verify_ws_token, verify_agent_key
from ws_manager import manager
from agent_protocol import MessageEnvelope, ServerCommand

logger = logging.getLogger(__name__)

router = APIRouter()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/api/v1")


async def _post_to_backend(path: str, payload: dict, api_key: str):
    """Fire-and-forget POST to Django backend with agent API key auth."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{BACKEND_URL}{path}",
                json=payload,
                headers={"X-Agent-API-Key": api_key},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status not in (200, 202):
                    body = await resp.text()
                    logger.warning(f"Backend POST {path} → {resp.status}: {body[:120]}")
                else:
                    logger.debug(f"Backend POST {path} → {resp.status}")
    except Exception as e:
        logger.error(f"_post_to_backend({path}) failed: {e}")


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
    db_pool = websocket.app.state.pool
    device_id = await verify_agent_key(db_pool, api_key)
    if not device_id:
        await websocket.close(code=1008, reason="Invalid API Key")
        return

    await manager.connect_agent(websocket, device_id)

    # Notify dashboards the agent came online
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
                    # 1. Broadcast to dashboards
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "agent_heartbeat",
                        "payload": {**env.payload, "device_id": device_id}
                    }))
                    # 2. Update last_seen in Django backend asynchronously
                    asyncio.create_task(
                        _post_to_backend(
                            f"/devices/{device_id}/heartbeat/",
                            env.payload,
                            api_key,
                        )
                    )

                elif env.event == "system_info":
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "agent_system_info",
                        "payload": {**env.payload, "device_id": device_id}
                    }))

                elif env.event == "inventory_info":
                    # 1. Broadcast to dashboards
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "agent_inventory_info",
                        "payload": {**env.payload, "device_id": device_id}
                    }))
                    # 2. Persist to backend
                    asyncio.create_task(
                        _post_to_backend(
                            f"/devices/{device_id}/ingest_inventory/",
                            env.payload,
                            api_key,
                        )
                    )

                elif env.event == "scan_results":
                    # 1. Broadcast live update to all dashboards
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "scan_results",
                        "payload": {**env.payload, "device_id": device_id}
                    }))
                    # 2. Persist results to Django backend asynchronously
                    asyncio.create_task(
                        _post_to_backend(
                            f"/devices/{device_id}/ingest_scan/",
                            env.payload,
                            api_key,
                        )
                    )

                elif env.event == "patch_result":
                    payload_with_device = {**env.payload, "device_id": device_id}
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "patch_result",
                        "payload": payload_with_device,
                    }))
                    # Persist deployment target result to Django backend
                    deployment_id = env.payload.get("deployment_id")
                    target_id = env.payload.get("target_id")
                    if deployment_id and target_id:
                        asyncio.create_task(
                            _post_to_backend(
                                f"/deployments/{deployment_id}/ingest_patch_result/",
                                payload_with_device,
                                api_key,
                            )
                        )

                elif env.event == "pong":
                    await manager.broadcast_to_dashboard(json.dumps({
                        "event": "pong",
                        "payload": {**env.payload, "device_id": device_id}
                    }))

            except Exception as e:
                logger.error(f"Error handling agent event from {device_id}: {e}")

    except WebSocketDisconnect:
        manager.disconnect(websocket, device_id, is_agent=True)
        await manager.broadcast_to_dashboard(json.dumps({
            "event": "agent_offline",
            "payload": {"device_id": device_id}
        }))
