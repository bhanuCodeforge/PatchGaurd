import asyncio
import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket, WebSocketDisconnect
from logging_utils import trace

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Maps dashboard user_id/session string to websocket list
        self.dashboard_connections: Dict[str, List[WebSocket]] = {}
        # Subscriptions mapping deployment_id -> set of dashboard websocket objects
        self.deployment_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Subscriptions mapping device_id -> set of dashboard websocket objects
        self.device_subscriptions: Dict[str, Set[WebSocket]] = {}
        # Maps agent_id strings to their active websocket
        self.agent_connections: Dict[str, WebSocket] = {}

    @trace
    async def connect_dashboard(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.dashboard_connections:
            self.dashboard_connections[user_id] = []
        self.dashboard_connections[user_id].append(websocket)
        logger.info(f"Dashboard User {user_id} connected.")

    @trace
    async def connect_agent(self, websocket: WebSocket, agent_id: str):
        await websocket.accept()
        if agent_id in self.agent_connections:
            # Old connection drop
            try:
                await self.agent_connections[agent_id].close(code=1000)
            except Exception:
                pass
        self.agent_connections[agent_id] = websocket
        logger.info(f"Agent Device {agent_id} connected.")

    def disconnect(self, websocket: WebSocket, identifier: str, is_agent: bool = False):
        if is_agent:
            if identifier in self.agent_connections and self.agent_connections[identifier] == websocket:
                del self.agent_connections[identifier]
                logger.info(f"Agent {identifier} disconnected.")
        else:
            if identifier in self.dashboard_connections:
                try:
                    self.dashboard_connections[identifier].remove(websocket)
                except ValueError:
                    pass
                if not self.dashboard_connections[identifier]:
                    del self.dashboard_connections[identifier]
            
            # Remove from all deployment subscriptions
            for dep_id, ws_set in self.deployment_subscriptions.items():
                if websocket in ws_set:
                    ws_set.remove(websocket)
            # Remove from all device subscriptions
            for dev_id, ws_set in self.device_subscriptions.items():
                if websocket in ws_set:
                    ws_set.remove(websocket)
            logger.info(f"Dashboard User {identifier} disconnected.")

    def subscribe_to_deployment(self, websocket: WebSocket, deployment_id: str):
        if deployment_id not in self.deployment_subscriptions:
            self.deployment_subscriptions[deployment_id] = set()
        self.deployment_subscriptions[deployment_id].add(websocket)

    def unsubscribe_from_deployment(self, websocket: WebSocket, deployment_id: str):
        if deployment_id in self.deployment_subscriptions:
            self.deployment_subscriptions[deployment_id].discard(websocket)

    def subscribe_to_device(self, websocket: WebSocket, device_id: str):
        if device_id not in self.device_subscriptions:
            self.device_subscriptions[device_id] = set()
        self.device_subscriptions[device_id].add(websocket)

    def unsubscribe_from_device(self, websocket: WebSocket, device_id: str):
        if device_id in self.device_subscriptions:
            self.device_subscriptions[device_id].discard(websocket)

    async def broadcast_to_dashboard(self, message: str):
        dead_sockets = []
        for user_id, ws_list in self.dashboard_connections.items():
            for ws in ws_list:
                try:
                    await ws.send_text(message)
                except (Exception, WebSocketDisconnect):
                    dead_sockets.append((user_id, ws))
        
        for uid, socket in dead_sockets:
            self.disconnect(socket, uid, is_agent=False)

    async def broadcast_to_deployment(self, deployment_id: str, message: str):
        if deployment_id in self.deployment_subscriptions:
            dead_sockets = []
            for ws in self.deployment_subscriptions[deployment_id]:
                try:
                    await ws.send_text(message)
                except (Exception, WebSocketDisconnect):
                    dead_sockets.append(ws)
            for socket in dead_sockets:
                self.unsubscribe_from_deployment(socket, deployment_id)

    async def broadcast_to_device_subscribers(self, device_id: str, message: str):
        """Send a message to all dashboard clients subscribed to a specific device."""
        if device_id in self.device_subscriptions:
            dead_sockets = []
            for ws in self.device_subscriptions[device_id]:
                try:
                    await ws.send_text(message)
                except (Exception, WebSocketDisconnect):
                    dead_sockets.append(ws)
            for socket in dead_sockets:
                self.unsubscribe_from_device(socket, device_id)

    @trace
    async def send_to_agent(self, agent_id: str, message: str) -> bool:
        if agent_id in self.agent_connections:
            try:
                await self.agent_connections[agent_id].send_text(message)
                return True
            except (Exception, WebSocketDisconnect):
                self.disconnect(self.agent_connections[agent_id], agent_id, is_agent=True)
        return False

    async def broadcast_to_all_agents(self, message: str):
        dead_agents = []
        for agent_id, ws in self.agent_connections.items():
            try:
                await ws.send_text(message)
            except (Exception, WebSocketDisconnect):
                dead_agents.append((agent_id, ws))
                
        for aid, socket in dead_agents:
            self.disconnect(socket, aid, is_agent=True)

    def get_online_agents(self) -> List[str]:
        return list(self.agent_connections.keys())

    def get_agent_count(self) -> int:
        return len(self.agent_connections)
        
    def get_dashboard_count(self) -> int:
        return sum(len(ws_list) for ws_list in self.dashboard_connections.values())

manager = ConnectionManager()
