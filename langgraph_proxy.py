"""
OpenAI-compatible proxy for LangGraph Cloud CME Agents
Translates OpenAI chat format to LangGraph Cloud API calls
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import httpx
import uuid
import json
import os
from datetime import datetime

app = FastAPI(title="LangGraph CME Proxy")

# LangGraph Cloud configuration
LANGGRAPH_URL = os.getenv("LANGGRAPH_URL", "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app")
LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY", "")

# Map LibreChat model names to LangGraph graph names
GRAPH_MAP = {
    # CME Instruments
    "research": "research",
    "clinical_practice": "clinical_practice",
    "gap_analysis": "gap_analysis",
    "needs_assessment": "needs_assessment",
    "learning_objectives": "learning_objectives",
    "curriculum_design": "curriculum_design",
    "research_protocol": "research_protocol",
    "marketing_plan": "marketing_plan",
    "grant_writer": "grant_writer",
    "prose_quality": "prose_quality",
    "compliance_review": "compliance_review",
    # CME Compositions
    "full_pipeline": "full_pipeline",
    "needs_package": "needs_package",
    "curriculum_package": "curriculum_package",
    "grant_package": "grant_package",
}


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


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "langgraph-cme-proxy"}


@app.get("/v1/models")
async def list_models():
    """List available models"""
    models = []
    for model_id in GRAPH_MAP.keys():
        models.append({
            "id": model_id,
            "object": "model",
            "created": int(datetime.now().timestamp()),
            "owned_by": "dhg-langgraph"
        })
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint"""
    
    # Get the graph name from model
    graph_name = GRAPH_MAP.get(request.model)
    if not graph_name:
        raise HTTPException(
            status_code=400, 
            detail=f"Unknown model: {request.model}. Available: {list(GRAPH_MAP.keys())}"
        )
    
    # Extract the last user message
    user_messages = [m for m in request.messages if m.role == "user"]
    if not user_messages:
        raise HTTPException(status_code=400, detail="No user message found")
    
    last_message = user_messages[-1].content
    
    # Build input for LangGraph
    input_data = {
        "topic": last_message,
        "messages": [{"role": m.role, "content": m.content} for m in request.messages]
    }
    
    headers = {
        "x-api-key": LANGCHAIN_API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Use runs/wait endpoint for synchronous execution
            response = await client.post(
                f"{LANGGRAPH_URL}/runs/wait",
                headers=headers,
                json={
                    "assistant_id": graph_name,
                    "input": input_data,
                    "config": {
                        "configurable": {}
                    }
                }
            )
            
            if response.status_code != 200:
                error_detail = response.text
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LangGraph error: {error_detail}"
                )
            
            result = response.json()
            
            # Extract the output from LangGraph response
            # The structure depends on your graph's output
            output = result.get("output", {})
            
            # Try to get synthesis or messages from the output
            if isinstance(output, dict):
                if "synthesis" in output:
                    result_text = output["synthesis"]
                elif "messages" in output and len(output["messages"]) > 0:
                    last_msg = output["messages"][-1]
                    result_text = last_msg.get("content", str(output))
                else:
                    result_text = json.dumps(output, indent=2)
            else:
                result_text = str(output)
            
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
            raise HTTPException(status_code=504, detail="Request timeout - LangGraph took too long")
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=2027)
