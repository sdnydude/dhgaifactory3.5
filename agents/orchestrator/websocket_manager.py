"""WebSocket Manager for DHG Orchestrator"""
import asyncio
import uuid
from typing import Dict, Any
from datetime import datetime
from fastapi import WebSocket
import structlog

logger = structlog.get_logger()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def connect(self, websocket: WebSocket, client_id: str | None = None) -> str:
        await websocket.accept()
        if not client_id:
            client_id = str(uuid.uuid4())
        self.active_connections[client_id] = websocket
        self.sessions[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "session_id": str(uuid.uuid4()),
            "authenticated": False,
        }
        logger.info("ws_connected", client_id=client_id, total=len(self.active_connections))
        return client_id

    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
        self.sessions.pop(client_id, None)
        logger.info("ws_disconnected", client_id=client_id, total=len(self.active_connections))

    async def send_message(self, client_id: str, message: Dict[str, Any]):
        ws = self.active_connections.get(client_id)
        if not ws:
            return
        try:
            await ws.send_json(message)
            logger.info("ws_message_sent", client_id=client_id, type=message.get("type"))
        except Exception as e:
            logger.error("ws_send_failed", client_id=client_id, error=str(e))
            self.disconnect(client_id)

    async def handle_client_message(self, client_id: str, message: Dict[str, Any]) -> Dict[str, Any] | None:
        logger.info("ws_message_received", client_id=client_id, message=message)
        t = message.get("type")
        data = message.get("data", {}) or message.get("payload", {})
        
        if t == "connection.init":
            self.sessions[client_id]["authenticated"] = True
            return {
                "type": "connection.ack",
                "payload": {
                    "session_id": self.sessions[client_id]["session_id"],
                    "server_version": "1.0.0",
                    "heartbeat_interval": 30000,
                    "capabilities": ["streaming", "agent_status"],
                },
            }
        if t == "ping":
            return {"type": "pong", "payload": {}}
        if t == "request.submit":
            req_id = str(uuid.uuid4())
            await self.send_message(client_id, {"type": "request.accepted", "payload": {"request_id": req_id}})
            asyncio.create_task(self._demo_flow(client_id, req_id, data))
            return None
        if t == "chat.message":
            content = data.get("content")
            return {"type": "chat.response", "payload": {"content": f"Echo: {content}"}}
        logger.warning("ws_unknown_type", client_id=client_id, type=t)
        return {"type": "error", "payload": {"code": "unknown_type", "message": f"Unknown type: {t}"}}

    async def _demo_flow(self, client_id: str, req_id: str, request_data: Dict):
        try:
            await asyncio.sleep(0.2)
            await self.send_message(client_id, {"type": "agent.status", "payload": {"request_id": req_id, "agent": "orchestrator", "status": "processing", "message": "Processing request..."}})
            await asyncio.sleep(0.5)
            content_id = str(uuid.uuid4())
            await self.send_message(client_id, {"type": "content.chunk", "payload": {"request_id": req_id, "content_id": content_id, "chunk": "# CME Content\n\n"}})
            await asyncio.sleep(0.3)
            await self.send_message(client_id, {"type": "content.chunk", "payload": {"request_id": req_id, "content_id": content_id, "chunk": "This is generated CME content.\n\n"}})
            await asyncio.sleep(0.3)
            await self.send_message(client_id, {"type": "content.complete", "payload": {"request_id": req_id, "content_id": content_id, "title": request_data.get("title", "Generated Content"), "format": "markdown", "metadata": {"generated_at": datetime.utcnow().isoformat()}}})
            await asyncio.sleep(0.2)
            await self.send_message(client_id, {"type": "validation.complete", "payload": {"request_id": req_id, "content_id": content_id, "overall_status": "passed", "checks": [{"check": "accme_compliance", "status": "passed"}], "warnings": [], "violations": []}})
        except Exception as e:
            logger.error("demo_flow_failed", client_id=client_id, error=str(e))


manager = ConnectionManager()
