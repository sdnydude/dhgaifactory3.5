"""
OpenAI-compatible proxy for CME Research Agent
Translates OpenAI chat format to Registry API research requests
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import uuid
from datetime import datetime

app = FastAPI(title="CME Research Proxy")

# Service URLs
REGISTRY_URL = "http://localhost:8500"

class Message(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4000
    stream: Optional[bool] = False

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]

@app.get("/v1/models")
async def list_models():
    """List available models"""
    return {
        "object": "list",
        "data": [
            {
                "id": "cme_research_agent",
                "object": "model",
                "created": int(datetime.now().timestamp()),
                "owned_by": "dhg"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint"""
    
    # Extract the last user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")
    
    last_message = user_messages[-1].content
    
    # Parse the message to extract research parameters
    # For now, use the message as the topic
    input_params = {
        "topic": last_message,
        "therapeutic_area": ["general"],
        "profession": ["physicians"],
        "specialty": ["internal_medicine"],
        "query_type": "evidence_review",
        "target_audience": "physicians",
        "date_range_from": "2021-01-01",
        "date_range_to": datetime.now().strftime("%Y-%m-%d"),
        "minimum_evidence_level": "LEVEL_3",
        "max_results": 50,
        "use_local_llm": False,
        "output_format": "cme_proposal"
    }
    
    # Create research request via Registry API
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Create research request
            response = await client.post(
                f"{REGISTRY_URL}/api/v1/research/requests",
                json={
                    "user_id": "librechat_user",
                    "agent_type": "cme_research",
                    "input_params": input_params
                }
            )
            
            if response.status_code != 201:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Registry error: {response.text}"
                )
            
            request_data = response.json()
            request_id = request_data["request_id"]
            
            # Return response with request ID
            result_text = f"""✅ Research request created successfully!

**Request ID:** {request_id}
**Topic:** {last_message}
**Status:** Pending

Your CME research request has been submitted. The agent will:
1. Search PubMed for peer-reviewed literature
2. Search current practice patterns via Perplexity
3. Review clinical practice guidelines
4. Grade evidence using GRADE methodology
5. Identify practice gaps
6. Generate a comprehensive CME proposal

You can check the status using request ID: {request_id}

Note: This is a basic integration. The full form with multi-select fields for therapeutic areas, professions, and specialties will be available soon.
"""
            
            return ChatCompletionResponse(
                id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
                created=int(datetime.now().timestamp()),
                model=request.model,
                choices=[{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": result_text
                    },
                    "finish_reason": "stop"
                }],
                usage={
                    "prompt_tokens": len(last_message.split()),
                    "completion_tokens": len(result_text.split()),
                    "total_tokens": len(last_message.split()) + len(result_text.split())
                }
            )
            
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request timeout")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/v1/research/requests/{request_id}")
async def get_request_status(request_id: str):
    """Get research request status"""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{REGISTRY_URL}/api/v1/research/requests/{request_id}"
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        
        return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2027)
