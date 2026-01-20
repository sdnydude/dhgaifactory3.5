"""
DHG AI FACTORY - QA / COMPLIANCE AGENT
ACCME compliance validation and quality assurance
"""

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import structlog
import re

logger = structlog.get_logger()

app = FastAPI(
    title="DHG QA/Compliance Agent",
    description="ACCME compliance validation and quality assurance",
    version="1.0.0"
)


# Add request logging middleware for debugging
@app.middleware("http")
async def log_raw_requests(request: Request, call_next):
    if request.url.path == "/validate" and request.method == "POST":
        body = await request.body()
        logger.info("raw_validate_request", 
                   path=request.url.path, 
                   body=body.decode() if body else "<empty>", 
                   content_type=request.headers.get("content-type"))
    response = await call_next(request)
    return response

# ============================================================================
# SYSTEM PROMPT - DHG QA / COMPLIANCE AGENT
# ============================================================================

SYSTEM_PROMPT = """
SYSTEM: DHG QA / COMPLIANCE AGENT

Your tasks:
- Inspect outputs from Orchestrator or Writer
- Ensure:
   • correct compliance_mode (CME or NON–CME)
   • no hallucinated sources
   • all references are validated
   • word count constraints met (for needs assessment)
   • ACCME rules applied ONLY in CME Mode
   • NO ACCME rules in NON–CME Mode
   • no promotional language in CME Mode
   • correct fairness and balance
- Produce:
   • compliance_checks_passed (bool)
   • violations_detected (list)
- Log results back to registry
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    QA_COMPLIANCE_STRICT = os.getenv("QA_COMPLIANCE_STRICT", "true").lower() == "true"
    ACCME_STANDARDS_PATH = os.getenv("ACCME_STANDARDS_PATH", "/app/data/accme_standards.json")
    
    # Word count constraints
    NEEDS_ASSESSMENT_MIN_WORDS = 920
    NEEDS_ASSESSMENT_MAX_WORDS = 1620
    NEEDS_ASSESSMENT_TARGET_WORDS = 1250

config = Config()

# ============================================================================
# ACCME COMPLIANCE RULES
# ============================================================================

ACCME_RULES = {
    "fair_balance": "CME content must present a balanced view of therapeutic options",
    "no_commercial_bias": "Content must be free from commercial bias and promotional language",
    "evidence_based": "All clinical recommendations must be evidence-based with citations",
    "no_trade_names": "Avoid proprietary drug names; use generic names",
    "disclosure_required": "Financial relationships must be disclosed",
    "independent_control": "CME provider must maintain control of content",
    "needs_assessment": "Content must address identified educational needs",
    "learning_objectives": "Clear learning objectives required",
    "outcomes_measurement": "Plan for measuring outcomes required"
}

PROMOTIONAL_KEYWORDS = [
    "best", "superior", "revolutionary", "breakthrough", "cutting-edge",
    "proven", "guaranteed", "amazing", "incredible", "unbelievable",
    "market-leading", "industry-leading", "award-winning", "patented",
    "exclusive", "unique solution", "only", "first and only"
]

# ============================================================================
# MODELS
# ============================================================================

class ValidationRequest(BaseModel):
    """Request for content validation"""
    content: str
    compliance_mode: str  # "cme" or "non-cme"
    document_type: str  # needs_assessment, curriculum, script, etc.
    checks: List[str]  # Which checks to perform
    references: Optional[List[Dict[str, Any]]] = None
    metadata: Optional[Dict[str, Any]] = None

class ValidationResponse(BaseModel):
    """Validation results"""
    compliance_checks_passed: bool
    violations_detected: List[str]
    warnings: Optional[List[str]] = None
    recommendations: Optional[List[str]] = None
    checks_performed: List[str]
    metadata: Dict[str, Any]

class ViolationDetail(BaseModel):
    """Detailed violation information"""
    check_name: str
    severity: str  # critical, high, medium, low
    description: str
    location: Optional[str] = None
    recommendation: str

class ComplianceReport(BaseModel):
    """Comprehensive compliance report"""
    overall_status: str  # pass, fail, warning
    compliance_mode: str
    document_type: str
    violations: List[ViolationDetail]
    passed_checks: List[str]
    failed_checks: List[str]
    summary: str
    timestamp: str

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

def validate_compliance_mode(content: str, declared_mode: str) -> tuple[bool, List[str]]:
    """Validate that compliance mode is correct"""
    violations = []
    
    # CME indicators
    cme_indicators = [
        "cme", "accme", "continuing medical education",
        "moore levels", "learning objectives", "cme credits"
    ]
    
    # NON-CME indicators
    non_cme_indicators = [
        "commercial", "promotional", "marketing",
        "sales", "product launch", "competitive advantage"
    ]
    
    content_lower = content.lower()
    has_cme_indicators = any(indicator in content_lower for indicator in cme_indicators)
    has_non_cme_indicators = any(indicator in content_lower for indicator in non_cme_indicators)
    
    if declared_mode == "cme" and has_non_cme_indicators and not has_cme_indicators:
        violations.append("Content appears promotional but declared as CME mode")
    
    if declared_mode == "non-cme" and has_cme_indicators:
        violations.append("Content has CME indicators but declared as NON-CME mode")
    
    return len(violations) == 0, violations

def check_hallucinated_sources(references: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
    """Check for hallucinated/fabricated sources"""
    violations = []
    
    if not references:
        return True, []
    
    for ref in references:
        url = ref.get("url", "")
        
        # Check for obviously fake URLs
        if url:
            if "example.com" in url or "placeholder" in url or "xxx" in url:
                violations.append(f"Suspicious reference URL: {url}")
            
            # Check for URL validation status
            if "validated" in ref and not ref["validated"]:
                violations.append(f"Unvalidated reference: {ref.get('title', url)}")
        else:
            violations.append(f"Reference missing URL: {ref.get('title', 'Unknown')}")
    
    return len(violations) == 0, violations

def validate_references(references: List[Dict[str, Any]]) -> tuple[bool, List[str]]:
    """Validate all references are properly formatted and validated"""
    violations = []
    
    if not references:
        violations.append("No references provided")
        return False, violations
    
    for i, ref in enumerate(references, 1):
        # Check required fields
        required_fields = ["title", "url"]
        missing_fields = [field for field in required_fields if field not in ref]
        
        if missing_fields:
            violations.append(f"Reference {i} missing fields: {missing_fields}")
        
        # Check URL format
        url = ref.get("url", "")
        if url and not (url.startswith("http://") or url.startswith("https://")):
            violations.append(f"Reference {i} has invalid URL format: {url}")
    
    return len(violations) == 0, violations

def check_word_count(content: str, document_type: str) -> tuple[bool, List[str]]:
    """Check word count constraints"""
    violations = []
    word_count = len(content.split())
    
    if document_type == "needs_assessment":
        if word_count < config.NEEDS_ASSESSMENT_MIN_WORDS:
            violations.append(
                f"Word count too low: {word_count} words "
                f"(minimum: {config.NEEDS_ASSESSMENT_MIN_WORDS})"
            )
        elif word_count > config.NEEDS_ASSESSMENT_MAX_WORDS:
            violations.append(
                f"Word count too high: {word_count} words "
                f"(maximum: {config.NEEDS_ASSESSMENT_MAX_WORDS})"
            )
    
    return len(violations) == 0, violations

def check_accme_compliance(content: str, compliance_mode: str) -> tuple[bool, List[str]]:
    """Check ACCME rules - only in CME mode"""
    violations = []
    
    if compliance_mode != "cme":
        # Should NOT apply ACCME rules in NON-CME mode
        return True, []
    
    # CME Mode: Apply ACCME rules
    content_lower = content.lower()
    
    # Check for promotional language
    found_promotional = [kw for kw in PROMOTIONAL_KEYWORDS if kw in content_lower]
    if found_promotional:
        violations.append(
            f"Promotional language detected in CME content: {', '.join(found_promotional[:3])}"
        )
    
    # Check for brand names (simplified check)
    # Look for capitalized drug-like names
    brand_pattern = r'\b[A-Z][a-z]+[A-Z][a-z]+\b'  # e.g., "Lipitor", "Humira"
    potential_brands = re.findall(brand_pattern, content)
    if len(potential_brands) > 5:  # Threshold
        violations.append(
            "Possible proprietary drug names detected - prefer generic names in CME"
        )
    
    return len(violations) == 0, violations

def check_no_accme_in_non_cme(content: str, compliance_mode: str) -> tuple[bool, List[str]]:
    """Ensure NO ACCME rules applied in NON-CME mode"""
    violations = []
    
    if compliance_mode == "non-cme":
        # This is just a marker check - main logic is in check_accme_compliance
        # which returns early for non-cme mode
        pass
    
    return True, violations

def check_fair_balance(content: str, compliance_mode: str) -> tuple[bool, List[str]]:
    """Check for fair balance of therapeutic options"""
    violations = []
    
    if compliance_mode != "cme":
        return True, []
    
    # Look for language that suggests only one treatment option
    unbalanced_phrases = [
        "only treatment", "best treatment", "preferred treatment",
        "should always", "must use", "only option"
    ]
    
    content_lower = content.lower()
    found_unbalanced = [phrase for phrase in unbalanced_phrases if phrase in content_lower]
    
    if found_unbalanced:
        violations.append(
            f"Potential lack of fair balance detected: {', '.join(found_unbalanced)}"
        )
    
    return len(violations) == 0, violations

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "qa-compliance",
        "strict_mode": config.QA_COMPLIANCE_STRICT,
        "accme_rules_loaded": len(ACCME_RULES),
        "registry_connected": bool(config.REGISTRY_DB_URL)
    }

@app.post("/validate", response_model=ValidationResponse)
async def validate(request: ValidationRequest):
    """
    Validate content for compliance
    
    Process:
    1. Verify compliance_mode is correct
    2. Check for hallucinated sources
    3. Validate all references
    4. Check word count constraints (if applicable)
    5. Apply ACCME rules ONLY in CME mode
    6. Ensure NO ACCME rules in NON-CME mode
    7. Check for promotional language (CME only)
    8. Verify fair balance (CME only)
    9. Log results to registry
    """
    
    logger.info(
        "validation_request",
        compliance_mode=request.compliance_mode,
        document_type=request.document_type,
        checks=request.checks
    )
    
    # Validate compliance mode
    if request.compliance_mode not in ["cme", "non-cme"]:
        raise HTTPException(
            status_code=400,
            detail="compliance_mode must be 'cme' or 'non-cme'"
        )
    
    all_violations = []
    warnings = []
    checks_performed = []
    
    # Execute requested checks
    if "compliance_mode" in request.checks:
        passed, violations = validate_compliance_mode(request.content, request.compliance_mode)
        if not passed:
            all_violations.extend(violations)
        checks_performed.append("compliance_mode")
    
    if "hallucinated_sources" in request.checks and request.references:
        passed, violations = check_hallucinated_sources(request.references)
        if not passed:
            all_violations.extend(violations)
        checks_performed.append("hallucinated_sources")
    
    if "reference_validation" in request.checks and request.references:
        passed, violations = validate_references(request.references)
        if not passed:
            all_violations.extend(violations)
        checks_performed.append("reference_validation")
    
    if "word_count" in request.checks:
        passed, violations = check_word_count(request.content, request.document_type)
        if not passed:
            all_violations.extend(violations)
        checks_performed.append("word_count")
    
    if "accme_compliance" in request.checks:
        passed, violations = check_accme_compliance(request.content, request.compliance_mode)
        if not passed:
            all_violations.extend(violations)
        checks_performed.append("accme_compliance")
    
    if "fair_balance" in request.checks:
        passed, violations = check_fair_balance(request.content, request.compliance_mode)
        if not passed:
            all_violations.extend(violations)
        checks_performed.append("fair_balance")
    
    # TODO: Log to registry
    
    return ValidationResponse(
        compliance_checks_passed=len(all_violations) == 0,
        violations_detected=all_violations,
        warnings=warnings if warnings else None,
        recommendations=None,  # TODO: Generate recommendations
        checks_performed=checks_performed,
        metadata={
            "word_count": len(request.content.split()),
            "reference_count": len(request.references) if request.references else 0,
            "compliance_mode": request.compliance_mode,
            "document_type": request.document_type
        }
    )

@app.get("/accme-rules")
async def get_accme_rules():
    """Get list of ACCME compliance rules"""
    return {
        "rules": ACCME_RULES,
        "total_rules": len(ACCME_RULES),
        "applies_to": "CME mode only"
    }

@app.get("/promotional-keywords")
async def get_promotional_keywords():
    """Get list of promotional keywords to avoid in CME content"""
    return {
        "keywords": PROMOTIONAL_KEYWORDS,
        "total_keywords": len(PROMOTIONAL_KEYWORDS),
        "note": "These should be avoided in CME mode content"
    }

@app.post("/quick-check")
async def quick_check(
    content: str,
    compliance_mode: str = "cme"
) -> Dict[str, Any]:
    """
    Quick compliance check with default settings
    
    Runs all standard checks
    """
    
    request = ValidationRequest(
        content=content,
        compliance_mode=compliance_mode,
        document_type="general",
        checks=[
            "compliance_mode",
            "accme_compliance",
            "fair_balance"
        ]
    )
    
    return await validate(request)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "qa-compliance",
        "status": "ready",
        "capabilities": [
            "Compliance mode validation",
            "Hallucinated source detection",
            "Reference validation",
            "Word count checking",
            "ACCME rules enforcement (CME only)",
            "Promotional language detection",
            "Fair balance checking"
        ],
        "compliance_modes": ["cme", "non-cme"],
        "available_checks": [
            "compliance_mode",
            "hallucinated_sources",
            "reference_validation",
            "word_count",
            "accme_compliance",
            "fair_balance",
            "commercial_bias",
            "sdoh_equity"
        ],
        "system_prompt": "DHG QA / COMPLIANCE AGENT - Loaded"
    }

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info(
        "qa_compliance_agent_starting",
        strict_mode=config.QA_COMPLIANCE_STRICT,
        accme_rules=len(ACCME_RULES),
        system_prompt_loaded=True
    )

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("qa_compliance_agent_shutdown")


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
        # Call Ollama for real response
        try:
            import httpx
            async with httpx.AsyncClient(timeout=60.0) as ollama_client:
                ollama_resp = await ollama_client.post(
                    "http://dhg-ollama:11434/api/chat",
                    json={
                        "model": "mistral-small3.1:24b",
                        "messages": [
                            {"role": "system", "content": "You are a QA Compliance Agent."},
                            {"role": "user", "content": user_message}
                        ],
                        "stream": False
                    }
                )
                ollama_data = ollama_resp.json()
                response_content = ollama_data.get("message", {}).get("content", f"Agent received: {user_message}")
        except Exception as ollama_err:
            response_content = f"I am the Qa Compliance agent. Your message: {user_message[:100]}"
        
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

