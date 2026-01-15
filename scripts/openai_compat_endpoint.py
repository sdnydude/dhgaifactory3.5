# OpenAI-Compatible Chat Completions Endpoint for DHG Medical LLM
# Appends to medical-llm/main.py

# ============================================================================
# OPENAI-COMPATIBLE CHAT COMPLETIONS (for LibreChat)
# ============================================================================

from typing import Union
import time
import uuid

class ChatMessage(BaseModel):
    """OpenAI chat message format"""
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: str = "medical-llm"
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
    """
    OpenAI-compatible chat completions endpoint for LibreChat integration.
    Routes to Ollama with medllama2 model.
    """
    metrics.AGENT_LLM_REQUESTS.labels(agent="medical-llm", model=config.OLLAMA_MODEL).inc()
    start_time = time.time()
    
    try:
        # Convert OpenAI format to Ollama format
        ollama_messages = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        for msg in request.messages:
            ollama_messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Call Ollama
        response = client.chat(
            model=config.OLLAMA_MODEL,
            messages=ollama_messages,
            options={
                "temperature": request.temperature or config.MEDICAL_LLM_TEMPERATURE,
                "num_predict": request.max_tokens or 2048
            }
        )
        
        # Extract response content
        assistant_content = response['message']['content']
        
        # Estimate tokens (rough approximation)
        prompt_tokens = sum(len(m.content.split()) for m in request.messages) * 4
        completion_tokens = len(assistant_content.split()) * 4
        
        elapsed = time.time() - start_time
        metrics.AGENT_LLM_LATENCY.labels(agent="medical-llm", model=config.OLLAMA_MODEL).observe(elapsed)
        
        logger.info("chat_completion_success", 
                   model=config.OLLAMA_MODEL, 
                   latency=elapsed,
                   prompt_tokens=prompt_tokens,
                   completion_tokens=completion_tokens)
        
        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:8]}",
            created=int(time.time()),
            model=request.model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(role="assistant", content=assistant_content),
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
        logger.error("chat_completion_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")

# Also add a models endpoint for LibreChat discovery
@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "medical-llm",
                "object": "model",
                "created": 1700000000,
                "owned_by": "dhg-ai-factory"
            }
        ]
    }
