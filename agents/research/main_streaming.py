"""
DHG Research Agent - OpenAI-Compatible API with Streaming Support
Provides medical research capabilities via Perplexity and PubMed
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import structlog
import time
import uuid
import json

# Import existing config and utilities
import sys
sys.path.append("/app")
from config import config

logger = structlog.get_logger()

app = FastAPI(title="DHG Research Agent")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# OPENAI-COMPATIBLE MODELS
# ============================================================================

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2048
    stream: Optional[bool] = False

class ChatCompletionChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage

# ============================================================================
# STREAMING HELPER
# ============================================================================

async def stream_chat_response(request: ChatCompletionRequest, content: str):
    """Generate SSE chunks for streaming response."""
    chat_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    # Split content into words for streaming effect
    words = content.split()
    
    # Stream each word
    for word in words:
        chunk_data = {
            "id": chat_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {"content": word + " "},
                "finish_reason": None
            }]
        }
        yield f"data: {json.dumps(chunk_data)}\n\n"
    
    # Send final chunk with finish_reason
    final_chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": request.model,
        "choices": [{
            "index": 0,
            "delta": {},
            "finish_reason": "stop"
        }]
    }
    yield f"data: {json.dumps(final_chunk)}\n\n"
    
    # Send terminator
    yield "data: [DONE]\n\n"

# ============================================================================
# CHAT COMPLETIONS ENDPOINT
# ============================================================================

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI-compatible chat completions endpoint with streaming support."""
    start_time = time.time()
    
    try:
        # Extract user message
        user_message = ""
        for msg in request.messages:
            if msg.role == "user":
                user_message = msg.content
        
        # Get LLM response via Ollama
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as ollama_client:
                ollama_resp = await ollama_client.post(
                    "http://dhg-ollama:11434/api/chat",
                    json={
                        "model": "qwen2.5:14b",
                        "messages": [
                            {"role": "system", "content": "You are a Medical Research Agent specializing in evidence-based research from PubMed and medical literature."},
                            {"role": "user", "content": user_message}
                        ],
                        "stream": False
                    }
                )
                ollama_data = ollama_resp.json()
                response_content = ollama_data.get("message", {}).get("content", f"Research Agent received: {user_message}")
        except Exception as ollama_err:
            logger.warning("ollama_fallback", error=str(ollama_err))
            response_content = f"I am the Research Agent. I can help you with medical research queries using PubMed and Perplexity. Your query: {user_message[:100]}"
        
        # If streaming requested, return SSE
        if request.stream:
            return StreamingResponse(
                stream_chat_response(request, response_content),
                media_type="text/event-stream"
            )
        
        # Otherwise return complete JSON response
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
        logger.error("chat_completion_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)"""
    return {
        "object": "list",
        "data": [{
            "id": "research-agent",
            "object": "model",
            "created": 1700000000,
            "owned_by": "dhg-ai-factory"
        }]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "agent": "research", "streaming": "enabled"}

# ============================================================================
# PERPLEXITY API INTEGRATION
# ============================================================================

import httpx

async def query_perplexity(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Query Perplexity API for web-grounded research."""
    api_key = config.PERPLEXITY_API_KEY
    if not api_key:
        return {"error": "PERPLEXITY_API_KEY not configured", "results": []}
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a medical research assistant. Provide evidence-based answers with citations to scientific literature."
                        },
                        {
                            "role": "user",
                            "content": query
                        }
                    ],
                    "max_tokens": 2048,
                    "return_citations": True
                }
            )
            response.raise_for_status()
            data = response.json()
            
            return {
                "source": "perplexity",
                "answer": data.get("choices", [{}])[0].get("message", {}).get("content", ""),
                "citations": data.get("citations", []),
                "model": data.get("model", "sonar"),
                "usage": data.get("usage", {})
            }
    except Exception as e:
        logger.error("perplexity_query_failed", error=str(e))
        return {"error": str(e), "results": []}

@app.post("/sources/perplexity/query")
async def query_perplexity_endpoint(query: str, max_results: int = 10):
    """Query Perplexity directly for medical research."""
    logger.info("perplexity_query", query=query[:100])
    
    result = await query_perplexity(query, max_results)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

# ============================================================================
# PUBMED/NCBI API INTEGRATION
# ============================================================================

async def query_pubmed(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Query PubMed via NCBI E-utilities API."""
    api_key = config.NCBI_API_KEY
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: Search for PMIDs
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance"
            }
            if api_key:
                search_params["api_key"] = api_key
            
            search_resp = await client.get(f"{base_url}/esearch.fcgi", params=search_params)
            search_resp.raise_for_status()
            search_data = search_resp.json()
            
            pmids = search_data.get("esearchresult", {}).get("idlist", [])
            total_count = int(search_data.get("esearchresult", {}).get("count", 0))
            
            if not pmids:
                return {
                    "source": "pubmed",
                    "results": [],
                    "total_count": 0,
                    "query": query
                }
            
            # Step 2: Fetch article details
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids),
                "retmode": "xml",
                "rettype": "abstract"
            }
            if api_key:
                fetch_params["api_key"] = api_key
            
            fetch_resp = await client.get(f"{base_url}/efetch.fcgi", params=fetch_params)
            fetch_resp.raise_for_status()
            
            # Parse XML response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(fetch_resp.text)
            
            results = []
            for article in root.findall(".//PubmedArticle"):
                try:
                    pmid = article.find(".//PMID").text if article.find(".//PMID") is not None else ""
                    title_elem = article.find(".//ArticleTitle")
                    title = title_elem.text if title_elem is not None and title_elem.text else "No title"
                    
                    abstract_texts = article.findall(".//AbstractText")
                    abstract = " ".join([
                        (at.text or "") for at in abstract_texts
                    ]) if abstract_texts else "No abstract available"
                    
                    # Get authors
                    authors = []
                    for author in article.findall(".//Author"):
                        lastname = author.find("LastName")
                        forename = author.find("ForeName")
                        if lastname is not None and lastname.text:
                            name = lastname.text
                            if forename is not None and forename.text:
                                name = f"{forename.text} {lastname.text}"
                            authors.append(name)
                    
                    # Get journal and date
                    journal_elem = article.find(".//Journal/Title")
                    journal = journal_elem.text if journal_elem is not None else "Unknown Journal"
                    
                    year_elem = article.find(".//PubDate/Year")
                    year = year_elem.text if year_elem is not None else ""
                    
                    results.append({
                        "pmid": pmid,
                        "title": title,
                        "abstract": abstract[:1000] + "..." if len(abstract) > 1000 else abstract,
                        "authors": authors[:5],
                        "journal": journal,
                        "year": year,
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
                    })
                except Exception as parse_err:
                    logger.warning("pubmed_parse_error", error=str(parse_err))
                    continue
            
            return {
                "source": "pubmed",
                "results": results,
                "total_count": total_count,
                "returned_count": len(results),
                "query": query
            }
            
    except Exception as e:
        logger.error("pubmed_query_failed", error=str(e))
        return {"error": str(e), "source": "pubmed", "results": []}

@app.post("/sources/pubmed/query")
async def query_pubmed_endpoint(query: str, max_results: int = 10):
    """Query PubMed for medical literature."""
    logger.info("pubmed_query", query=query[:100])
    
    result = await query_pubmed(query, max_results)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result
