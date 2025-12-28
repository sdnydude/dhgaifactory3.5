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
            model = data.get("model", "auto")
            mode = data.get("mode", "auto")
            
            # Determine target agent based on model selection
            target_agent_url = None
            if "medical" in model or model == "auto":
                 # Use config from main.py (imported or injected? safer to rely on known service names)
                 target_agent_url = "http://medical-llm:8000"
            elif "claude" in model:
                 target_agent_url = "http://medical-llm:8000" # Using Medical LLM as proxy for now (it has prompt logic)
            
            if not target_agent_url:
                target_agent_url = "http://medical-llm:8000" # Default

            try:
                # Notify processing
                await self.send_message(client_id, {
                    "type": "agent.status", 
                    "payload": {"status": "processing", "agent": model}
                })

                # Call Agent (We rely on dependency injection from main.py)
                if hasattr(self, 'agent_client'):
                    # Construct simple payload for generic agent interaction
                    # Note: specialized agents expect specific schemas. 
                    # For Phase 3, we map a simple chat to the "generate" endpoint of medical-llm
                    payload = {
                        "task": "cme_script", # Defaulting to script for chat interaction
                        "topic": content, # Using content as topic
                        "compliance_mode": mode,
                        "style": "conversational"
                    }
                    
                    # Make the call
                    response = await self.agent_client.call_agent(
                        target_agent_url,
                        "generate",
                        payload
                    )
                    
                    return {
                        "type": "chat.response", 
                        "payload": {
                            "content": response.get("content", "No content generated"),
                            "metadata": response.get("metadata")
                        }
                    }
                else:
                    return {"type": "chat.response", "payload": {"content": "Error: Agent Client not initialized"}}

            except Exception as e:
                logger.error("agent_routing_failed", error=str(e))
                return {"type": "chat.response", "payload": {"content": f"Error communicating with agent: {str(e)}"}}

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
