#!/bin/bash
# Add OpenAI-compatible chat completions endpoint to all DHG agents
# Run on .251

AGENTS="research curriculum outcomes competitor-intel qa-compliance visuals"
BASE_DIR="/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/agents"

ENDPOINT_CODE='

# ============================================================================
# OPENAI-COMPATIBLE CHAT COMPLETIONS (for LibreChat)
# ============================================================================

import time
import uuid

class ChatMessage(BaseModel):
    """OpenAI chat message format"""
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: str = "agent"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False

class ChatCompletionChoice(BaseModel):
    """OpenAI chat completion choice"""
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionUsage(BaseModel):
    """Token usage info"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage

@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint for LibreChat."""
    start_time = time.time()
    
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
        
        # Simple echo response for now - each agent can customize
        response_content = f"Agent received: {user_message}"
        
        elapsed = time.time() - start_time
        prompt_tokens = len(user_message.split()) * 4
        completion_tokens = len(response_content.split()) * 4
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=response_content),
                    finish_reason="stop"
                )
            ],
            usage=ChatCompletionUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [{"id": "agent", "object": "model", "created": 1700000000, "owned_by": "dhg-ai-factory"}]
    }
'

for agent in $AGENTS; do
    echo "Adding endpoint to $agent..."
    
    # Check if endpoint already exists
    if grep -q "v1/chat/completions" "$BASE_DIR/$agent/main.py"; then
        echo "  Skipping $agent - endpoint already exists"
        continue
    fi
    
    # Append the endpoint code
    echo "$ENDPOINT_CODE" >> "$BASE_DIR/$agent/main.py"
    echo "  Done: $agent"
done

echo "All agents updated!"
