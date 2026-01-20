"""
LogoMaker Agent - Premium Logo & Icon Generation
Connects to Nano Banana Pro (Gemini 3 Pro Image) for Fortune 500 quality brand assets.
"""
import os
import asyncio
import base64
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="LogoMaker Agent",
    description="Premium logo and icon generation for Fortune 500 quality brand assets",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_PATH = Path("/mnt/4tb/dhg-storage/logo-maker")
STORAGE_PATH.mkdir(parents=True, exist_ok=True)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "logomaker"
    messages: List[ChatMessage]
    stream: bool = False


class NanoBananaClient:
    """Client for Nano Banana Pro (Gemini 3 Pro Image) API"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_name = "gemini-2.0-flash-exp"
        self._client = None
        self._initialized = False
    
    async def initialize(self):
        if not self.api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.warning("no_api_key", message="GOOGLE_API_KEY not set")
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai
            self._initialized = True
            logger.info("nano_banana_initialized", model=self.model_name)
            return True
        except ImportError:
            logger.warning("sdk_missing", message="google-generativeai not installed")
            return False
        except Exception as e:
            logger.error("init_failed", error=str(e))
            return False
    
    async def generate_logo(
        self,
        brand_name: str,
        industry: str,
        values: List[str],
        style: str,
        color_preferences: str = ""
    ) -> Dict[str, Any]:
        """Generate a premium logo using Nano Banana Pro"""
        
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized or not self._client:
            return {"status": "error", "error": "Nano Banana Pro not available"}
        
        prompt = self._build_logo_prompt(brand_name, industry, values, style, color_preferences)
        
        try:
            model = self._client.GenerativeModel(self.model_name)
            response = await asyncio.to_thread(
                model.generate_content, prompt
            )
            
            image_data = self._extract_image(response)
            
            if image_data:
                file_id = str(uuid.uuid4())[:8]
                safe_name = brand_name.lower().replace(" ", "_")
                filename = f"{safe_name}_{file_id}.png"
                filepath = STORAGE_PATH / filename
                
                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(image_data))
                
                return {
                    "status": "success",
                    "image_base64": image_data,
                    "filename": filename,
                    "path": str(filepath),
                    "prompt_used": prompt
                }
            else:
                return {"status": "no_image", "error": "Model did not return image"}
                
        except Exception as e:
            logger.error("generation_failed", error=str(e))
            return {"status": "error", "error": str(e)}
    
    def _extract_image(self, response) -> Optional[str]:
        """Extract image data from Gemini response"""
        if hasattr(response, "parts"):
            for part in response.parts:
                if hasattr(part, "inline_data") and hasattr(part.inline_data, "data"):
                    if part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                        return base64.b64encode(part.inline_data.data).decode("utf-8")
        
        if hasattr(response, "candidates"):
            for candidate in response.candidates:
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
                    for part in candidate.content.parts:
                        if hasattr(part, "inline_data") and hasattr(part.inline_data, "data"):
                            if part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                                return base64.b64encode(part.inline_data.data).decode("utf-8")
        return None
    
    def _build_logo_prompt(
        self,
        brand_name: str,
        industry: str,
        values: List[str],
        style: str,
        color_preferences: str
    ) -> str:
        """Build Fortune 500 quality logo prompt"""
        
        quality_modifiers = """
Premium brand identity, Fortune 500 quality, Apple-level design sophistication,
perfect visual balance, professional polish, C-suite presentation ready,
clean vector aesthetic, scalable design, transparent background PNG
"""
        
        style_mods = {
            "modern": "minimalist contemporary, clean geometry, dynamic energy, innovation-forward",
            "classic": "timeless elegance, refined heritage, established authority, sophisticated tradition",
            "tech": "futuristic precision, digital innovation, cutting-edge, sleek technology",
            "healthcare": "trust and credibility, caring professionalism, life-affirming, warm expertise",
            "finance": "stability and strength, premium authority, refined elegance, timeless sophistication",
            "luxury": "exclusive refinement, understated excellence, bespoke craftsmanship, heritage quality"
        }
        
        style_modifier = style_mods.get(style.lower(), style_mods["modern"])
        values_str = ", ".join(values) if values else "professional, innovative, trustworthy"
        
        color_line = ""
        if color_preferences:
            color_line = f"Color Preferences: {color_preferences}"
        
        prompt = f"""Create a premium logo for: {brand_name}

Industry: {industry}
Brand Values: {values_str}
Style Direction: {style_modifier}
{color_line}

{quality_modifiers}

Generate a sophisticated, memorable logo mark that embodies these qualities.
No text in the logo - pure symbolic mark only.
Transparent background.
"""
        return prompt


nano_banana = NanoBananaClient()


DISCOVERY_STATE: Dict[str, Dict] = {}


def get_discovery_response(user_message: str, session_id: str) -> str:
    """Handle the brand discovery conversation flow"""
    
    if session_id not in DISCOVERY_STATE:
        DISCOVERY_STATE[session_id] = {"step": 0, "data": {}}
    
    state = DISCOVERY_STATE[session_id]
    step = state["step"]
    
    if step == 0:
        state["step"] = 1
        return """Welcome to LogoMaker! I create Fortune 500 quality logos and icon sets.

Let me learn about your brand. First question:

**What is your company or brand name?**"""
    
    elif step == 1:
        state["data"]["brand_name"] = user_message.strip()
        state["step"] = 2
        brand = state["data"]["brand_name"]
        return f"""Got it - **{brand}**

**What industry or sector are you in?**
(e.g., Technology, Healthcare, Finance, Retail, Professional Services)"""
    
    elif step == 2:
        state["data"]["industry"] = user_message.strip()
        state["step"] = 3
        return """**What 3 words best describe how you want customers to feel about your brand?**
(e.g., innovative, trustworthy, premium, approachable, bold)"""
    
    elif step == 3:
        values = [v.strip() for v in user_message.replace(",", " ").split() if v.strip()][:5]
        state["data"]["values"] = values
        state["step"] = 4
        return """**What style direction fits your brand best?**

1. **Modern** - Clean, minimal, contemporary
2. **Classic** - Timeless, elegant, established  
3. **Tech** - Futuristic, digital, innovative
4. **Healthcare** - Trustworthy, caring, professional
5. **Finance** - Strong, stable, premium
6. **Luxury** - Exclusive, refined, sophisticated

Just type the style name or number."""
    
    elif step == 4:
        style_map = {"1": "modern", "2": "classic", "3": "tech", "4": "healthcare", "5": "finance", "6": "luxury"}
        style = style_map.get(user_message.strip(), user_message.strip().lower())
        state["data"]["style"] = style
        state["step"] = 5
        return """**Any color preferences?**

Type specific colors or palettes you like (e.g., "blue and gold", "earth tones", "vibrant purple")

Or type "no preference" and I will choose based on your brand values."""
    
    elif step == 5:
        color_pref = user_message.strip() if user_message.lower() != "no preference" else ""
        state["data"]["color_preferences"] = color_pref
        state["step"] = 6
        
        data = state["data"]
        values_display = ", ".join(data["values"])
        color_display = color_pref if color_pref else "Designer choice"
        return f"""Perfect! Here is your brand brief:

**Brand:** {data["brand_name"]}
**Industry:** {data["industry"]}
**Values:** {values_display}
**Style:** {data["style"].title()}
**Colors:** {color_display}

Type **"generate"** to create your logo, or tell me if you want to change anything."""
    
    elif step == 6:
        if "generate" in user_message.lower() or "create" in user_message.lower() or "go" in user_message.lower():
            state["step"] = 7
            return "GENERATE_NOW"
        else:
            return "What would you like to change? Just tell me, or type **generate** when ready."
    
    else:
        return "Your logo has been generated! Type **new** to start a new logo project."


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "LogoMaker Agent",
        "nano_banana_ready": nano_banana._initialized,
        "storage_path": str(STORAGE_PATH)
    }




@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "logomaker",
                "object": "model",
                "created": 1700000000,
                "owned_by": "dhg"
            }
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat endpoint"""
    
    session_id = str(uuid.uuid4())[:8]
    
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        user_message = "start"
    
    for msg in request.messages:
        if msg.role == "assistant" and "What is your company" in msg.content:
            DISCOVERY_STATE[session_id] = {"step": 1, "data": {}}
    
    response_text = get_discovery_response(user_message, session_id)
    
    if response_text == "GENERATE_NOW":
        state = DISCOVERY_STATE.get(session_id, {})
        data = state.get("data", {})
        
        result = await nano_banana.generate_logo(
            brand_name=data.get("brand_name", "Brand"),
            industry=data.get("industry", "Technology"),
            values=data.get("values", ["professional"]),
            style=data.get("style", "modern"),
            color_preferences=data.get("color_preferences", "")
        )
        
        if result.get("status") == "success":
            saved_path = result.get("path")
            response_text = f"""Your logo has been generated!

**Saved to:** `{saved_path}`

The logo features:
- Premium Fortune 500 quality design
- Clean, scalable vector aesthetic  
- Transparent background
- Optimized for all use cases

Type **icons** to generate a complete icon set, or **new** to start a new project."""
        else:
            error_msg = result.get("error", "Unknown error")
            response_text = f"""I encountered an issue generating your logo: {error_msg}

Please try again or adjust your brand parameters."""
    
    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(datetime.now().timestamp()),
        "model": "logomaker",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": response_text
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(user_message.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(user_message.split()) + len(response_text.split())
        }
    }


@app.on_event("startup")
async def startup():
    await nano_banana.initialize()
    logger.info("logomaker_started", storage=str(STORAGE_PATH))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8012)
