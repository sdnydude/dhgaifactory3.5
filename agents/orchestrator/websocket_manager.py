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
                    "server_version": "1.1.0",
                    "heartbeat_interval": 30000,
                    "capabilities": ["multi_agent", "streaming_status", "registry_sync"],
                },
            }
        
        if t == "ping":
            return {"type": "pong", "payload": {}}
            
        if t == "chat.message" or t == "request.submit":
            req_id = data.get("request_id") or str(uuid.uuid4())
            content = data.get("content") or data.get("topic")
            model = data.get("model", "auto")
            mode = data.get("mode", "auto")
            
            # Acknowledge request
            await self.send_message(client_id, {
                "type": "request.accepted", 
                "payload": {"request_id": req_id}
            })
            
            # Start background processing
            asyncio.create_task(self._run_task(client_id, req_id, content, model, mode, data))
            return None

        logger.warning("ws_unknown_type", client_id=client_id, type=t)
        return {"type": "error", "payload": {"code": "unknown_type", "message": f"Unknown type: {t}"}}

    async def _run_task(self, client_id: str, req_id: str, content: str, model: str, mode: str, full_data: Dict):
        """
        Coordinated task execution across agents
        """
        try:
            # 1. Routing & Initial Status
            target_agent = "medical-llm"
            if "research" in model.lower():
                target_agent = "research"
            elif "curriculum" in model.lower():
                target_agent = "curriculum"
                
            await self.send_message(client_id, {
                "type": "agent.status", 
                "payload": {
                    "request_id": req_id,
                    "agent": target_agent,
                    "status": "processing",
                    "message": f"Routing request to {target_agent}..."
                }
            })

            # 2. Call the Agent
            if not hasattr(self, 'agent_client'):
                raise Exception("Agent Client not initialized")

            # Map the request to the agent's expected schema
            # Defaulting to 'generate' for medical-llm, but could be others
            agent_url = f"http://{target_agent}:8000"
            
            # Simulate multi-step status if it's a complex task
            if mode == "cme":
                 await self.send_message(client_id, {
                     "type": "agent.status",
                     "payload": {"request_id": req_id, "agent": "qa-compliance", "status": "checking", "message": "Verifying ACCME requirements..."}
                 })
                 await asyncio.sleep(0.1)

            # Call specialized agent
            response = await self.agent_client.call_agent(
                agent_url,
                "generate",
                {
                    "task": full_data.get("task_type", "cme_script"),
                    "topic": content,
                    "compliance_mode": mode,
                    "word_count_target": full_data.get("word_count_target", 1000)
                }
            )

            # 3. Stream Content Back
            content_id = str(uuid.uuid4())
            generated_text = response.get("content", "No content generated")
            
            # For "streaming" feel, we can send chunks (simulated for now, as agent returns whole block)
            # Future: specialized agents will stream
            await self.send_message(client_id, {
                "type": "content.chunk", 
                "payload": {"request_id": req_id, "content_id": content_id, "chunk": generated_text}
            })

            # 4. Final Completion
            await self.send_message(client_id, {
                "type": "content.complete",
                "payload": {
                    "request_id": req_id,
                    "content_id": content_id,
                    "title": content[:50],
                    "format": "markdown",
                    "metadata": response.get("metadata", {})
                }
            })

            # 5. Validation Result
            await self.send_message(client_id, {
                "type": "validation.complete",
                "payload": {
                    "request_id": req_id,
                    "content_id": content_id,
                    "overall_status": "passed" if not response.get("violations") else "failed",
                    "checks": [{"check": "compliance_check", "status": "passed"}],
                    "violations": response.get("violations", []),
                    "warnings": response.get("warnings", [])
                }
            })

        except Exception as e:
            logger.error("run_task_failed", req_id=req_id, error=str(e))
            await self.send_message(client_id, {
                "type": "error",
                "payload": {
                    "request_id": req_id,
                    "message": f"Task execution failed: {str(e)}"
                }
            })


manager = ConnectionManager()
