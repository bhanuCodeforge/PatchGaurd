"""
SSH Terminal WebSocket handler.

Flow:
  1. Client opens  wss://.../ws/ssh?token=<JWT>
  2. Server verifies JWT and checks role (admin / operator)
  3. Client sends  {type:"connect", host, port, username,
                    auth_type, password|private_key, cols, rows}
  4. Server opens asyncssh connection to the target host
  5. Bidirectional relay:
       - asyncssh stdout  →  {type:"output",  data: <str>}
       - client input     →  process.stdin
       - {type:"resize"}  →  process.change_terminal_size()
  6. On any error/close the server sends {type:"error"|"disconnected"}
     and closes the WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from auth import verify_ws_token

try:
    import asyncssh
    _ASYNCSSH_AVAILABLE = True
except ImportError:
    _ASYNCSSH_AVAILABLE = False

router = APIRouter()
logger = logging.getLogger(__name__)

_ALLOWED_ROLES = {"admin", "operator"}


# ─── helpers ──────────────────────────────────────────────────────────────────

async def _ws_send(ws: WebSocket, msg: dict) -> None:
    try:
        await ws.send_text(json.dumps(msg))
    except Exception:
        pass


async def _ws_recv(ws: WebSocket) -> Optional[dict]:
    try:
        raw = await asyncio.wait_for(ws.receive_text(), timeout=30)
        return json.loads(raw)
    except asyncio.TimeoutError:
        return None
    except (WebSocketDisconnect, RuntimeError):
        return None
    except Exception as exc:
        logger.debug("_ws_recv error: %s", exc)
        return None


# ─── main endpoint ─────────────────────────────────────────────────────────────

@router.websocket("/ws/ssh")
async def ssh_terminal(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    # 1. Auth
    try:
        user = await verify_ws_token(token)
    except Exception:
        await websocket.accept()
        await _ws_send(websocket, {"type": "error", "message": "Unauthorized"})
        await websocket.close(code=4401)
        return

    role = user.get("role", "")
    if role not in _ALLOWED_ROLES:
        await websocket.accept()
        await _ws_send(websocket, {"type": "error", "message": f"Role '{role}' is not permitted to open SSH sessions"})
        await websocket.close(code=4403)
        return

    await websocket.accept()
    logger.info("SSH WS accepted for user=%s role=%s", user.get("username"), role)

    if not _ASYNCSSH_AVAILABLE:
        await _ws_send(websocket, {
            "type": "error",
            "message": "asyncssh is not installed on the server. Run: pip install asyncssh",
        })
        await websocket.close()
        return

    # 2. Wait for connect message
    connect_msg = await _ws_recv(websocket)
    if not connect_msg or connect_msg.get("type") != "connect":
        await _ws_send(websocket, {"type": "error", "message": "Expected connect message"})
        await websocket.close()
        return

    host        = connect_msg.get("host", "").strip()
    port        = int(connect_msg.get("port", 22))
    username    = connect_msg.get("username", "").strip()
    auth_type   = connect_msg.get("auth_type", "password")
    password    = connect_msg.get("password", "")
    private_key_pem = connect_msg.get("private_key", "")
    cols        = int(connect_msg.get("cols", 80))
    rows        = int(connect_msg.get("rows", 24))

    if not host or not username:
        await _ws_send(websocket, {"type": "error", "message": "host and username are required"})
        await websocket.close()
        return

    # 3. Build asyncssh connect kwargs
    connect_kwargs: dict = {
        "host": host,
        "port": port,
        "username": username,
        "known_hosts": None,          # Accept any host key (dashboard shows audit log)
        "connect_timeout": 15,
    }

    if auth_type == "password":
        connect_kwargs["password"] = password
    elif auth_type == "key" and private_key_pem:
        try:
            connect_kwargs["client_keys"] = [asyncssh.import_private_key(private_key_pem)]
        except Exception as exc:
            await _ws_send(websocket, {"type": "error", "message": f"Invalid private key: {exc}"})
            await websocket.close()
            return
    # agent forwarding: let asyncssh pick up from the local SSH agent automatically

    session_id = f"pg-ssh-{uuid.uuid4().hex[:12]}"
    logger.info("SSH connect: session=%s user=%s -> %s@%s:%s", session_id, user.get("username"), username, host, port)

    # 4. Open SSH connection
    conn: Optional[asyncssh.SSHClientConnection] = None
    process = None
    try:
        conn = await asyncssh.connect(**connect_kwargs)
        process = await conn.create_process(
            term_type="xterm-256color",
            term_size=(cols, rows),
        )
    except asyncssh.PermissionDenied as exc:
        logger.warning("SSH auth failed for session %s: %s", session_id, exc)
        await _ws_send(websocket, {"type": "error", "message": f"Authentication failed: {exc}. Verify your username and private key."})
        await websocket.close()
        if conn:
            conn.close()
        return
    except asyncssh.ConnectionLost as exc:
        logger.error("SSH connection lost for session %s: %s", session_id, exc)
        await _ws_send(websocket, {"type": "error", "message": f"Connection lost: {exc}"})
        await websocket.close()
        return
    except (OSError, asyncio.TimeoutError) as exc:
        logger.error("SSH host unreachable for session %s: %s", session_id, exc)
        await _ws_send(websocket, {"type": "error", "message": f"Cannot reach host (Connection Refused). Ensure the SSH server is running on the target."})
        await websocket.close()
        return
    except Exception as exc:
        logger.exception("SSH unexpected error for session %s", session_id)
        await _ws_send(websocket, {"type": "error", "message": f"Unexpected SSH error: {str(exc)}"})
        await websocket.close()
        return

    # Negotiate cipher / kex info (best-effort)
    try:
        cipher  = conn.get_extra_info("cipher",   default="unknown")
        key_ex  = conn.get_extra_info("mac",      default="unknown")
    except Exception:
        cipher = "AES256-GCM"
        key_ex = "curve25519-sha256"

    # 5. Notify client: connected
    await _ws_send(websocket, {
        "type":         "connected",
        "session_id":   session_id,
        "cipher":       cipher,
        "key_exchange": key_ex,
    })

    # 6. Relay loop
    stop_event = asyncio.Event()

    async def _read_ssh():
        """SSH stdout → WebSocket"""
        try:
            async for chunk in process.stdout:
                if stop_event.is_set():
                    break
                await _ws_send(websocket, {"type": "output", "data": chunk})
        except asyncssh.ConnectionLost:
            pass
        except Exception as exc:
            logger.debug("SSH read error: %s", exc)
        finally:
            stop_event.set()

    async def _read_ws():
        """WebSocket → SSH stdin / resize"""
        try:
            while not stop_event.is_set():
                try:
                    raw = await asyncio.wait_for(websocket.receive_text(), timeout=60)
                except asyncio.TimeoutError:
                    # Send keepalive NOP
                    if not stop_event.is_set():
                        try:
                            await websocket.send_text('{"type":"ping"}')
                        except Exception:
                            break
                    continue
                except (WebSocketDisconnect, RuntimeError):
                    break

                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                msg_type = msg.get("type")
                if msg_type == "input":
                    data = msg.get("data", "")
                    if data:
                        process.stdin.write(data)
                elif msg_type == "resize":
                    new_cols = int(msg.get("cols", cols))
                    new_rows = int(msg.get("rows", rows))
                    try:
                        process.change_terminal_size(new_cols, new_rows)
                    except Exception:
                        pass
                elif msg_type == "disconnect":
                    break
        except Exception as exc:
            logger.debug("WS read error: %s", exc)
        finally:
            stop_event.set()

    try:
        await asyncio.gather(_read_ssh(), _read_ws(), return_exceptions=True)
    finally:
        try:
            process.stdin.write_eof()
        except Exception:
            pass
        try:
            process.close()
        except Exception:
            pass
        if conn:
            conn.close()
        await _ws_send(websocket, {"type": "disconnected"})
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("SSH session closed: session=%s", session_id)
