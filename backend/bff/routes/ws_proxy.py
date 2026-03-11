"""
BFF Routes — WebSocket pass-through for /ws/* paths.

Bridges the Angular client WebSocket connection to the realtime FastAPI
service using a bidirectional relay loop.  Auth is validated at the
realtime service; the BFF forwards the raw query string (including the
JWT token) unchanged.

Architecture:
  Angular  <──WS──>  BFF /ws/*  <──WS──>  Realtime Service /ws/*
"""
import asyncio
import logging
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from bff.config import REALTIME_WS_URL

logger = logging.getLogger(__name__)
router = APIRouter()

CONNECT_TIMEOUT = 10  # seconds to wait for upstream WS handshake


@router.websocket("/ws/{path:path}")
async def websocket_proxy(path: str, websocket: WebSocket):
    """
    Bidirectional WebSocket relay.

    The full query string (e.g. ?token=...) is forwarded verbatim so the
    realtime service can authenticate the connection with its own logic.
    """
    await websocket.accept()

    # Build the upstream WS URL with original query string
    query_string = websocket.scope.get("query_string", b"").decode()
    upstream_url = f"{REALTIME_WS_URL}/ws/{path}"
    if query_string:
        upstream_url = f"{upstream_url}?{query_string}"

    logger.debug("WS proxy: %s → %s", path, upstream_url)

    try:
        async with websockets.connect(
            upstream_url,
            open_timeout=CONNECT_TIMEOUT,
            ping_interval=20,
            ping_timeout=10,
        ) as upstream_ws:

            async def client_to_upstream():
                """Forward messages from Angular client → upstream realtime."""
                try:
                    while True:
                        try:
                            data = await websocket.receive_text()
                        except Exception:
                            break
                        try:
                            await upstream_ws.send(data)
                        except Exception:
                            break
                except asyncio.CancelledError:
                    pass

            async def upstream_to_client():
                """Forward messages from upstream realtime → Angular client."""
                try:
                    async for message in upstream_ws:
                        try:
                            if isinstance(message, bytes):
                                await websocket.send_bytes(message)
                            else:
                                await websocket.send_text(message)
                        except Exception:
                            break
                except asyncio.CancelledError:
                    pass
                except Exception as exc:
                    logger.debug("Upstream WS closed: %s", exc)

            # Run both relay directions concurrently; stop when either ends
            done, pending = await asyncio.wait(
                [
                    asyncio.create_task(client_to_upstream()),
                    asyncio.create_task(upstream_to_client()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )
            for task in pending:
                task.cancel()

    except websockets.exceptions.InvalidStatusCode as exc:
        logger.warning("Upstream WS rejected connection (status %s) for path %s", exc.status_code, path)
        await websocket.close(code=1008, reason="Upstream rejected connection")
    except (OSError, websockets.exceptions.WebSocketException) as exc:
        logger.warning("WS proxy connection error for %s: %s", path, exc)
        await websocket.close(code=1011, reason="Gateway error")
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("WS proxy unexpected error for %s: %s", path, exc)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
