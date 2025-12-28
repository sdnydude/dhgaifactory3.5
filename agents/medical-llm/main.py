"""
DHG AI FACTORY - MEDICAL LLM & NLP AGENT
Handles medical language model operations, evidence synthesis, and clinical content generation
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
import structlog
import ollama
from shared import metrics

logger = structlog.get_logger()

app = FastAPI(
    title="DHG Medical LLM & NLP Agent",
    description="Medical language model and NLP processing",
    version="1.0.0"
)

# ============================================================================
# SYSTEM PROMPT - DHG MEDICAL LLM & NLP AGENT
# ============================================================================

SYSTEM_PROMPT = """
SYSTEM: DHG MEDICAL LLM & NLP AGENT

You are the dedicated Medical LLM & NLP Agent for DHG AI Factory.

Your tasks:
- Extract ICD-10 codes from text
- Suggest Quality Measures (NQF/CMS/MIPS)
- Perform clinical Named Entity Recognition (diseases, drugs, devices, labs)
- Normalize concepts to UMLS, SNOMED, ICD-10, MeSH
- Summarize clinical trials from evidence
- Summarize guidelines (ACR, ACC/AHA, ADA, GOLD, GINA, IDSA, etc.)
- Identify SDOH / equity issues
- Provide structured, evidence-grounded medical insights

Models available:
- MedLlama2
- Meditron
- BioMistral
- MedGemma
- ClinicalBERT
- BioBERT
- GatorTron
- NIM Llama 3.1 70B

Requirements:
- NEVER hallucinate guideline content
- Use only validated references (if provided)
- NEVER guess ICD-10 or QI measures—must infer or say "none found"
- Log ALL tasks to Postgres registry
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "medllama2") # Default to medical model
    MEDICAL_LLM_TEMPERATURE = float(os.getenv("MEDICAL_LLM_TEMPERATURE", "0.3"))

config = Config()
# Configure Ollama client
client = ollama.Client(host=config.OLLAMA_HOST)

# ============================================================================
# MODELS
# ============================================================================

class GenerateRequest(BaseModel):
    """Request for medical content generation"""
    task: str = "general" # needs_assessment, summary, ner, etc.
    topic: str
    research_data: Optional[Dict[str, Any]] = None
    compliance_mode: str = "auto"
    word_count_target: int = 500
    include_sdoh: bool = True
    include_equity: bool = True
    reference_count_min: int = 1
    reference_count_max: int = 5
    style: str = "conversational" # cleo_abram_narrative, clinical, academic
    structure: str = "general" # scr_framework, imrad, etc.
    corrections: Optional[List[str]] = None

class GenerateResponse(BaseModel):
    """Response from medical content generation"""
    content: str
    references: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    icd10_codes: Optional[List[str]] = None
    quality_measures: Optional[List[str]] = None
    clinical_entities: Optional[Dict[str, List[str]]] = None

class NERRequest(BaseModel):
    """Named Entity Recognition request"""
    text: str
    entity_types: List[str] = ["disease", "drug", "device", "lab", "procedure"]

class NERResponse(BaseModel):
    """Named Entity Recognition response"""
    entities: Dict[str, List[Dict[str, Any]]]
    normalized_concepts: Dict[str, Any]

class ICD10Request(BaseModel):
    """ICD-10 code extraction request"""
    text: str
    context: Optional[str] = None

class ICD10Response(BaseModel):
    """ICD-10 code extraction response"""
    codes: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]

class QualityMeasureRequest(BaseModel):
    """Quality measure suggestion request"""
    topic: str
    condition: Optional[str] = None
    intervention: Optional[str] = None

class QualityMeasureResponse(BaseModel):
    """Quality measure suggestion response"""
    measures: List[Dict[str, Any]]
    sources: List[str]  # NQF, CMS, MIPS

class GuidelineSummaryRequest(BaseModel):
    """Guideline summary request"""
    guideline_source: str  # ACR, ACC/AHA, ADA, etc.
    topic: str
    references: List[Dict[str, Any]]

class GuidelineSummaryResponse(BaseModel):
    """Guideline summary response"""
    summary: str
    key_recommendations: List[str]
    evidence_levels: Dict[str, str]
    references_used: List[Dict[str, Any]]

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint with real GPU metrics"""
    gpu_stats = metrics.get_gpu_metrics()
    return {
        "status": "healthy",
        "agent": "medical-llm",
        "gpu": gpu_stats,
        "models_available": [
            "MedLlama2", "Meditron", "BioMistral", "MedGemma",
            "ClinicalBERT", "BioBERT", "GatorTron", "NIM Llama 3.1 70B"
        ],
        "registry_connected": bool(config.REGISTRY_DB_URL)
    }

@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """
    Generate medical content based on research and requirements
    """
    logger.info("generate_request", topic=request.topic, task=request.task)
    
    # Construct research context from provided data
    research_context = ""
    if request.research_data:
        research_context = f"Research Context:\n{request.research_data.get('summary', '')}\n"
        if 'references' in request.research_data:
            research_context += "Available References:\n" + "\n".join(
                [f"- {r.get('title', 'Untitled')} ({r.get('url', 'No URL')})" 
                 for r in request.research_data.get('references', [])]
            )

    prompt = (
        f"Task: {request.task}\n"
        f"Topic: {request.topic}\n"
        f"Style: {request.style}\n"
        f"Compliance Mode: {request.compliance_mode}\n"
        f"{research_context}\n"
        f"Requirements: Target word count {request.word_count_target}. Use AMA style references."
    )
    
    if request.corrections:
        prompt += f"\n\nCorrections to apply: {', '.join(request.corrections)}"

    try:
        response = client.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': prompt}
            ],
            options={'temperature': config.MEDICAL_LLM_TEMPERATURE}
        )
        content = response['message']['content']
    except Exception as e:
        logger.error("ollama_generation_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Ollama generation failed: {str(e)}")

    # Use references from research_data if available
    references = []
    if request.research_data and 'references' in request.research_data:
        references = request.research_data['references'][:request.reference_count_max]
    
    return GenerateResponse(
        content=content,
        references=references,
        metadata={
            "agent": "medical-llm-v3.5",
            "model": config.OLLAMA_MODEL,
            "gpu_stats": metrics.get_gpu_metrics(),
            "word_count": len(content.split())
        }
    )


@app.post("/ner", response_model=NERResponse)
async def named_entity_recognition(request: NERRequest):
    """
    Perform clinical Named Entity Recognition using medical LLM
    """
    logger.info("ner_request", text_length=len(request.text))
    
    prompt = f"Perform clinical NER on this text. Extract entities of types: {', '.join(request.entity_types)}. Return JSON with entity types as keys and lists of entity objects (with 'text' and 'type' fields) as values.\n\nText: {request.text}"
    
    try:
        response = client.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': "You are a clinical NER extracter. Return JSON object with entity types as keys and lists of entity objects as values."},
                {'role': 'user', 'content': prompt}
            ],
            format="json"
        )
        import json
        result = json.loads(response['message']['content'])
        
        # Normalize the result to expected format
        normalized_entities: Dict[str, List[Dict[str, Any]]] = {}
        for key, entities in result.items():
            if isinstance(entities, list):
                normalized_list = []
                for entity in entities:
                    if isinstance(entity, str):
                        normalized_list.append({"text": entity, "type": key})
                    elif isinstance(entity, dict):
                        normalized_list.append(entity)
                normalized_entities[key] = normalized_list
        
        return NERResponse(entities=normalized_entities, normalized_concepts={})
    except Exception as e:
        logger.error("ner_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/icd10", response_model=ICD10Response)
async def extract_icd10(request: ICD10Request):
    """
    Extract ICD-10 codes from clinical text using medical LLM
    """
    logger.info("icd10_request", text_length=len(request.text))
    
    prompt = f"Identify possible ICD-10 codes and descriptions for the following clinical text. Return JSON as a list of objects with 'code' and 'description'.\n\nText: {request.text}"
    
    try:
        response = client.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': "You are an expert medical coder. Return JSON only. If no codes found, return empty list. Do not hallucinate."},
                {'role': 'user', 'content': prompt}
            ],
            format="json"
        )
        import json
        result = json.loads(response['message']['content'])
        
        # Handle different JSON structures
        if isinstance(result, list):
            codes = result
        elif isinstance(result, dict) and 'codes' in result:
            codes = result['codes']
        else:
            codes = []
        
        # Safely build confidence scores
        confidence_scores = {}
        for c in codes:
            if isinstance(c, dict) and 'code' in c:
                confidence_scores[c['code']] = 0.9
        
        return ICD10Response(codes=codes, confidence_scores=confidence_scores)
    except Exception as e:
        logger.error("icd10_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/quality-measures", response_model=QualityMeasureResponse)
async def suggest_quality_measures(request: QualityMeasureRequest):
    """
    Suggest Quality Measures (NQF/CMS/MIPS) based on topic/condition
    """
    logger.info("quality_measures_request", topic=request.topic)
    
    prompt = f"Suggest relevant NQF, CMS, or MIPS quality measures for: {request.topic}. Condition: {request.condition}. Return JSON only."
    
    try:
        response = client.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': "Expert in healthcare quality measures. Return JSON list of {id, title, source, description}."},
                {'role': 'user', 'content': prompt}
            ],
            format="json"
        )
        import json
        measures = json.loads(response['message']['content'])
        return QualityMeasureResponse(measures=measures, sources=list(set(m.get('source') for m in measures if m.get('source'))))
    except Exception as e:
        logger.error("quality_measures_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/guideline-summary", response_model=GuidelineSummaryResponse)
async def summarize_guideline(request: GuidelineSummaryRequest):
    """
    Summarize clinical guidelines from provided references
    """
    logger.info("guideline_summary_request", source=request.guideline_source, topic=request.topic)
    
    ref_text = "\n".join([f"- {r.get('title')}: {r.get('url')}" for r in request.references])
    prompt = f"Summarize {request.guideline_source} guidelines for {request.topic} using these references:\n{ref_text}\nReturn JSON with summary, key_recommendations (list), and evidence_levels (dict)."

    try:
        response = client.chat(
            model=config.OLLAMA_MODEL,
            messages=[
                {'role': 'system', 'content': "Expert medical guideline summarizer. Return JSON only. No hallucinations."},
                {'role': 'user', 'content': prompt}
            ],
            format="json"
        )
        import json
        data = json.loads(response['message']['content'])
        return GuidelineSummaryResponse(
            summary=data.get('summary', ''),
            key_recommendations=data.get('key_recommendations', []),
            evidence_levels=data.get('evidence_levels', {}),
            references_used=request.references
        )
    except Exception as e:
        logger.error("guideline_summary_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "medical-llm",
        "status": "ready",
        "capabilities": [
            "Medical content generation",
            "Named Entity Recognition",
            "ICD-10 extraction",
            "Quality measure suggestions",
            "Guideline summarization",
            "SDOH/equity analysis"
        ],
        "system_prompt": "DHG MEDICAL LLM & NLP AGENT - Loaded"
    }

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("medical_llm_agent_starting", system_prompt_loaded=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("medical_llm_agent_shutdown")
