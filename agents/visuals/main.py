"""
DHG AI FACTORY - VISUALS AGENT
Medical image generation using Nano Banana Pro (Gemini 3 Pro Image)
"""

import os
import io
import base64
import asyncio
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="DHG Visuals Agent",
    description="Medical visualization and image generation using Nano Banana Pro",
    version="1.0.0"
)

# Enable CORS for web UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    MODEL_NAME = "gemini-3-pro-image-preview"  # Nano Banana Pro
    IMAGE_STORAGE_PATH = "/app/generated_images"
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")

config = Config()


# ============================================================================
# DATABASE IMAGE STORE
# ============================================================================

class ImageStore:
    """Store and retrieve generated images from PostgreSQL"""
    
    def __init__(self, db_url: str = None):
        self.db_url = db_url or config.REGISTRY_DB_URL
        self._pool = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        if not self.db_url:
            logger.warning("image_store_no_db", message="REGISTRY_DB_URL not set")
            return False
        
        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(self.db_url, min_size=1, max_size=5)
            logger.info("image_store_connected")
            return True
        except Exception as e:
            logger.error("image_store_init_failed", error=str(e))
            return False
    
    async def save_image(
        self,
        topic: str,
        visual_type: str,
        image_data: bytes,
        prompt_used: str,
        style: str = None,
        compliance_mode: str = None,
        metadata: dict = None
    ) -> str:
        """Save generated image to database, returns image_id"""
        if not self._pool:
            await self.initialize()
        
        if not self._pool:
            logger.warning("image_store_not_available")
            return None
        
        try:
            async with self._pool.acquire() as conn:
                result = await conn.fetchrow("""
                    INSERT INTO generated_images 
                    (topic, visual_type, style, prompt_used, image_data, 
                     file_size_bytes, generation_model, compliance_mode, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    RETURNING image_id
                """, 
                    topic,
                    visual_type,
                    style,
                    prompt_used,
                    image_data,
                    len(image_data),
                    config.MODEL_NAME,
                    compliance_mode,
                    metadata
                )
                image_id = str(result["image_id"])
                logger.info("image_saved", image_id=image_id, size=len(image_data))
                return image_id
        except Exception as e:
            logger.error("image_save_failed", error=str(e))
            return None
    
    async def get_image(self, image_id: str) -> dict:
        """Retrieve image by ID"""
        if not self._pool:
            await self.initialize()
        
        if not self._pool:
            return None
        
        try:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT image_id, topic, visual_type, style, prompt_used,
                           image_data, mime_type, file_size_bytes, generation_model,
                           compliance_mode, metadata, created_at
                    FROM generated_images
                    WHERE image_id = $1
                """, image_id)
                
                if row:
                    return dict(row)
                return None
        except Exception as e:
            logger.error("image_get_failed", error=str(e))
            return None
    
    async def list_images(self, limit: int = 20, offset: int = 0) -> list:
        """List recent images (without image_data)"""
        if not self._pool:
            await self.initialize()
        
        if not self._pool:
            return []
        
        try:
            async with self._pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT image_id, topic, visual_type, style, 
                           file_size_bytes, generation_model, created_at
                    FROM generated_images
                    ORDER BY created_at DESC
                    LIMIT $1 OFFSET $2
                """, limit, offset)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error("image_list_failed", error=str(e))
            return []


image_store = ImageStore()


# ============================================================================
# MODELS
# ============================================================================

class VisualsRequest(BaseModel):
    """Request for visual generation"""
    topic: str
    visual_type: str = "infographic"  # slide, chart, infographic, diagram, illustration
    style: str = "medical-professional"  # medical-professional, educational, modern-minimal
    data_points: Optional[List[str]] = None
    include_text: Optional[str] = None
    aspect_ratio: str = "16:9"  # 16:9, 4:3, 1:1, 9:16
    compliance_mode: str = "cme"  # cme, non-cme

class VisualsResponse(BaseModel):
    """Response with generated visual"""
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    prompt_used: str
    generation_model: str
    status: str
    error: Optional[str] = None
    metadata: Dict[str, Any]

class EditRequest(BaseModel):
    """Request to edit an existing image"""
    image_base64: str
    edit_prompt: str
    visual_type: str = "infographic"

# ============================================================================
# NANO BANANA PRO CLIENT
# ============================================================================

class NanoBananaClient:
    """Client for Nano Banana Pro (Gemini 3 Pro Image) API"""
    
    def __init__(self, api_key: str = None):
        # Read API key fresh from environment (not from config which may be stale)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model_name = config.MODEL_NAME
        self._client = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize the Gemini client"""
        # Re-read API key from environment in case it wasn't available at __init__ time
        if not self.api_key:
            self.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            logger.warning("nano_banana_no_api_key", message="GOOGLE_API_KEY not set")
            return False
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai
            self._initialized = True
            logger.info("nano_banana_initialized", model=self.model_name)
            return True
        except ImportError:
            logger.warning("nano_banana_sdk_missing", message="google-generativeai not installed")
            return False
        except Exception as e:
            logger.error("nano_banana_init_failed", error=str(e))
            return False
    
    async def generate_image(
        self,
        prompt: str,
        visual_type: str = "infographic",
        style: str = "medical-professional",
        aspect_ratio: str = "16:9"
    ) -> Dict[str, Any]:
        """Generate an image using Nano Banana Pro"""
        
        if not self._initialized:
            await self.initialize()
        
        if not self._initialized or not self._client:
            return {
                "status": "fallback",
                "image_url": self._generate_fallback_url(prompt),
                "prompt_used": prompt,
                "error": "Nano Banana Pro not available, using fallback"
            }
        
        enhanced_prompt = self._build_medical_prompt(prompt, visual_type, style, aspect_ratio)
        
        try:
            model = self._client.GenerativeModel(self.model_name)
            
            # Generate with image-generation prompt
            response = await asyncio.to_thread(
                model.generate_content,
                enhanced_prompt
            )
            
            # Check for image in response
            image_data = None
            if hasattr(response, 'parts'):
                for part in response.parts:
                    if hasattr(part, 'inline_data') and hasattr(part.inline_data, 'data'):
                        if part.inline_data.mime_type and part.inline_data.mime_type.startswith('image/'):
                            image_data = base64.b64encode(part.inline_data.data).decode('utf-8')
                            break
            
            # Also check for candidates structure
            if not image_data and hasattr(response, 'candidates'):
                for candidate in response.candidates:
                    if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and hasattr(part.inline_data, 'data'):
                                if part.inline_data.mime_type and part.inline_data.mime_type.startswith('image/'):
                                    image_data = base64.b64encode(part.inline_data.data).decode('utf-8')
                                    break
            
            if image_data:
                return {
                    "status": "success",
                    "image_base64": image_data,
                    "prompt_used": enhanced_prompt,
                    "error": None
                }
            else:
                return {
                    "status": "no_image",
                    "image_url": self._generate_fallback_url(prompt),
                    "prompt_used": enhanced_prompt,
                    "error": "Model did not return image"
                }
                
        except Exception as e:
            logger.error("nano_banana_generation_failed", error=str(e))
            return {
                "status": "error",
                "image_url": self._generate_fallback_url(prompt),
                "prompt_used": enhanced_prompt,
                "error": str(e)
            }
    
    def _build_medical_prompt(
        self,
        topic: str,
        visual_type: str,
        style: str,
        aspect_ratio: str
    ) -> str:
        """Build an optimized prompt for medical visuals"""
        
        style_descriptors = {
            "medical-professional": "clean, professional medical illustration style with soft blues and greens, clinical accuracy",
            "educational": "clear educational diagram style with labeled elements, easy to understand",
            "modern-minimal": "modern minimalist design with clean lines, subtle gradients, contemporary healthcare aesthetic"
        }
        
        type_descriptors = {
            # Original types
            "infographic": "professional medical infographic with icons, data visualization, and clear hierarchy",
            "slide": "professional presentation slide suitable for medical education",
            "chart": "clinical data chart or graph with clear labels and professional appearance",
            "diagram": "anatomical or process diagram with accurate labeling",
            "illustration": "medical illustration with professional accuracy and educational value",
            # CME-specific types
            "thumbnail": "eye-catching video or podcast thumbnail with bold text, suitable for YouTube or LMS course cards",
            "certificate": "professional CME completion certificate with elegant borders, accreditation logos placeholder, and formal typography",
            "logo": "clean medical logo with legible text, suitable for podcast or educational activity branding",
            "timeline": "horizontal or vertical timeline showing treatment progression, disease stages, or clinical milestones",
            "comparison": "side-by-side comparison visual for treatment options, drug classes, or clinical approaches",
            "anatomical": "focused anatomical illustration of specific body part or system with labels",
            "flowchart": "clinical decision flowchart or algorithm with clear decision points and pathways",
            "case_study": "patient case presentation visual with HIPAA-safe placeholder demographics and key clinical findings",
            "moa": "mechanism of action diagram showing drug or treatment pathway at molecular or cellular level",
            # Social/Marketing types
            "social_post": "social media card optimized for Instagram or LinkedIn with engaging visuals and minimal text",
            "banner": "wide banner image for website headers, email campaigns, or event promotion",
            "avatar": "professional avatar or profile image for AI agents or educational personas",
            # Data-heavy types
            "heatmap": "data heatmap visualization showing intensity or frequency patterns",
            "dashboard": "multi-metric dashboard display with KPIs, gauges, and summary statistics",
            "scorecard": "performance scorecard or summary card with key metrics and visual indicators"
        }
        
        style_desc = style_descriptors.get(style, style_descriptors["medical-professional"])
        type_desc = type_descriptors.get(visual_type, type_descriptors["infographic"])
        
        prompt = f"""Generate a {type_desc} about: {topic}

Style: {style_desc}
Aspect ratio: {aspect_ratio}
Requirements:
- Suitable for continuing medical education (CME)
- Accurate and professional medical representation
- Clear, readable text if included
- High quality, publication-ready output
- No misleading or inaccurate medical information"""
        
        return prompt
    
    def _generate_fallback_url(self, topic: str) -> str:
        """Generate a fallback placeholder URL"""
        safe_topic = topic.replace(' ', '_').replace('/', '-')[:50]
        return f"https://via.placeholder.com/1200x675/2563eb/ffffff?text={safe_topic}"


nano_banana = NanoBananaClient()

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    all_types = [
        "infographic", "slide", "chart", "diagram", "illustration",
        "thumbnail", "certificate", "logo", "timeline", "comparison",
        "anatomical", "flowchart", "case_study", "moa",
        "social_post", "banner", "avatar",
        "heatmap", "dashboard", "scorecard"
    ]
    return {
        "status": "healthy",
        "agent": "visuals",
        "model": config.MODEL_NAME,
        "api_configured": bool(config.GOOGLE_API_KEY),
        "db_configured": bool(config.REGISTRY_DB_URL),
        "capabilities": all_types,
        "total_visual_types": len(all_types)
    }


@app.post("/generate", response_model=VisualsResponse)
async def generate_visual(request: VisualsRequest):
    """
    Generate medical visual using Nano Banana Pro
    
    Supports: infographic, slide, chart, diagram, illustration
    """
    
    logger.info(
        "visual_generation_request",
        topic=request.topic,
        visual_type=request.visual_type,
        style=request.style
    )
    
    prompt_additions = []
    if request.data_points:
        prompt_additions.append(f"Include data points: {', '.join(request.data_points)}")
    if request.include_text:
        prompt_additions.append(f"Include text: {request.include_text}")
    
    full_topic = request.topic
    if prompt_additions:
        full_topic += ". " + ". ".join(prompt_additions)
    
    result = await nano_banana.generate_image(
        prompt=full_topic,
        visual_type=request.visual_type,
        style=request.style,
        aspect_ratio=request.aspect_ratio
    )
    
    # Save to database if image was generated
    image_id = None
    if result.get("image_base64") and result.get("status") == "success":
        image_bytes = base64.b64decode(result["image_base64"])
        image_id = await image_store.save_image(
            topic=request.topic,
            visual_type=request.visual_type,
            image_data=image_bytes,
            prompt_used=result.get("prompt_used", full_topic),
            style=request.style,
            compliance_mode=request.compliance_mode,
            metadata={
                "aspect_ratio": request.aspect_ratio,
                "data_points": request.data_points,
                "include_text": request.include_text
            }
        )
    
    return VisualsResponse(
        image_url=f"/images/{image_id}" if image_id else result.get("image_url"),
        image_base64=result.get("image_base64"),
        prompt_used=result.get("prompt_used", full_topic),
        generation_model=config.MODEL_NAME,
        status=result.get("status", "unknown"),
        error=result.get("error"),
        metadata={
            "image_id": image_id,
            "visual_type": request.visual_type,
            "style": request.style,
            "aspect_ratio": request.aspect_ratio,
            "compliance_mode": request.compliance_mode,
            "generated_at": datetime.utcnow().isoformat(),
            "stored_in_db": image_id is not None
        }
    )


@app.post("/edit")
async def edit_visual(request: EditRequest):
    """Edit an existing visual with new instructions"""
    
    logger.info("visual_edit_request", edit_prompt=request.edit_prompt)
    
    if not nano_banana._initialized:
        await nano_banana.initialize()
    
    if not nano_banana._initialized:
        raise HTTPException(
            status_code=503,
            detail="Nano Banana Pro not available for editing"
        )
    
    return {
        "status": "pending",
        "message": "Image editing requires multimodal input - implementation in progress"
    }


@app.get("/styles")
async def get_available_styles():
    """Get available visual styles and types"""
    return {
        "visual_types": {
            "core": [
                {"id": "infographic", "name": "Infographic", "description": "Data-rich visual with icons and text"},
                {"id": "slide", "name": "Presentation Slide", "description": "Single slide for medical presentations"},
                {"id": "chart", "name": "Chart/Graph", "description": "Clinical data visualization"},
                {"id": "diagram", "name": "Diagram", "description": "Anatomical or process diagram"},
                {"id": "illustration", "name": "Illustration", "description": "Medical illustration"}
            ],
            "cme_specific": [
                {"id": "thumbnail", "name": "Thumbnail", "description": "Video/podcast thumbnail for YouTube or LMS"},
                {"id": "certificate", "name": "Certificate", "description": "CME completion certificate"},
                {"id": "logo", "name": "Logo", "description": "Medical/podcast logo with text"},
                {"id": "timeline", "name": "Timeline", "description": "Treatment progression or milestones"},
                {"id": "comparison", "name": "Comparison", "description": "Side-by-side treatment options"},
                {"id": "anatomical", "name": "Anatomical", "description": "Focused body part/system illustration"},
                {"id": "flowchart", "name": "Flowchart", "description": "Clinical decision algorithm"},
                {"id": "case_study", "name": "Case Study", "description": "Patient case presentation visual"},
                {"id": "moa", "name": "Mechanism of Action", "description": "Drug/treatment pathway diagram"}
            ],
            "social_marketing": [
                {"id": "social_post", "name": "Social Post", "description": "Instagram/LinkedIn optimized card"},
                {"id": "banner", "name": "Banner", "description": "Website header or event banner"},
                {"id": "avatar", "name": "Avatar", "description": "Profile image for agents/personas"}
            ],
            "data_heavy": [
                {"id": "heatmap", "name": "Heatmap", "description": "Data intensity visualization"},
                {"id": "dashboard", "name": "Dashboard", "description": "Multi-metric display with KPIs"},
                {"id": "scorecard", "name": "Scorecard", "description": "Performance summary with indicators"}
            ]
        },
        "styles": [
            {"id": "medical-professional", "name": "Medical Professional", "description": "Clean clinical aesthetic"},
            {"id": "educational", "name": "Educational", "description": "Clear labeling for learning"},
            {"id": "modern-minimal", "name": "Modern Minimal", "description": "Contemporary healthcare design"}
        ],
        "aspect_ratios": ["16:9", "4:3", "1:1", "9:16"],
        "total_visual_types": 19
    }


@app.get("/images/{image_id}")
async def get_image(image_id: str):
    """Retrieve a generated image by ID"""
    from fastapi.responses import Response
    
    image = await image_store.get_image(image_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return Response(
        content=image["image_data"],
        media_type=image.get("mime_type", "image/png"),
        headers={
            "Content-Disposition": f"inline; filename={image_id}.png",
            "X-Image-Topic": image.get("topic", ""),
            "X-Image-Type": image.get("visual_type", "")
        }
    )


@app.get("/images/{image_id}/info")
async def get_image_info(image_id: str):
    """Get metadata about a generated image (without the binary data)"""
    image = await image_store.get_image(image_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Return metadata without the binary data
    return {
        "image_id": str(image["image_id"]),
        "topic": image["topic"],
        "visual_type": image["visual_type"],
        "style": image["style"],
        "prompt_used": image["prompt_used"],
        "file_size_bytes": image["file_size_bytes"],
        "generation_model": image["generation_model"],
        "compliance_mode": image["compliance_mode"],
        "created_at": image["created_at"].isoformat() if image["created_at"] else None,
        "image_url": f"/images/{image_id}"
    }


@app.get("/images")
async def list_images(limit: int = 20, offset: int = 0):
    """List recently generated images"""
    images = await image_store.list_images(limit=limit, offset=offset)
    
    return {
        "images": [
            {
                "image_id": str(img["image_id"]),
                "topic": img["topic"],
                "visual_type": img["visual_type"],
                "style": img["style"],
                "file_size_bytes": img["file_size_bytes"],
                "created_at": img["created_at"].isoformat() if img["created_at"] else None,
                "image_url": f"/images/{img['image_id']}"
            }
            for img in images
        ],
        "count": len(images),
        "limit": limit,
        "offset": offset
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "visuals",
        "status": "ready",
        "model": "Nano Banana Pro (Gemini 3 Pro Image)",
        "capabilities": [
            "Medical infographic generation",
            "Presentation slide creation",
            "Clinical chart generation",
            "Anatomical diagram creation",
            "Medical illustration",
            "Database image storage"
        ],
        "api_configured": bool(config.GOOGLE_API_KEY),
        "db_configured": bool(config.REGISTRY_DB_URL)
    }


@app.on_event("startup")
async def startup_event():
    """Initialize Nano Banana Pro and image store on startup"""
    logger.info("visuals_agent_starting")
    await nano_banana.initialize()
    await image_store.initialize()
    logger.info(
        "visuals_agent_ready", 
        nano_banana_ready=nano_banana._initialized,
        image_store_ready=image_store._pool is not None
    )


@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("visuals_agent_shutdown")
    if image_store._pool:
        await image_store._pool.close()

