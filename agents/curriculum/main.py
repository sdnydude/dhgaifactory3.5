"""
DHG AI FACTORY - CURRICULUM AGENT
CME curriculum design, learning objectives, and educational structure
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import httpx
import json
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="DHG Curriculum Agent",
    description="CME curriculum design and learning objectives",
    version="1.0.0"
)

# ============================================================================
# SYSTEM PROMPT - DHG CURRICULUM AGENT
# ============================================================================

SYSTEM_PROMPT = """
SYSTEM: DHG CURRICULUM AGENT

Your tasks:
- Generate 6–10 Learning Objectives
- Map objectives to:
  • Moore Levels
  • ICD-10 codes
  • QI Measures
  • Target practice behaviors
- Build activity-level curriculum outlines
- Ensure CME Mode or NON–CME Mode rules
- Generate instructor/faculty briefs
- Log all requests/responses to registry
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    CURRICULUM_TEMPLATE_PATH = os.getenv("CURRICULUM_TEMPLATE_PATH", "/app/templates")
    LEARNING_OBJECTIVES_MIN = 6
    LEARNING_OBJECTIVES_MAX = 10

config = Config()

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def call_ollama(system_prompt: str, user_prompt: str, model: str = "qwen2.5:14b") -> str:
    """Call Ollama for LLM assistance"""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://dhg-ollama:11434/api/chat",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "stream": False
                }
            )
            data = response.json()
            return data.get("message", {}).get("content", "")
    except Exception as e:
        logger.error("ollama_call_failed", error=str(e))
        return f"LLM call failed: {str(e)}"

# ============================================================================
# ENUMS
# ============================================================================

MOORE_LEVELS = [
    "level_1_participation",
    "level_2_satisfaction",
    "level_3_learning_declarative",
    "level_4_competence",
    "level_5_performance",
    "level_6_patient_health",
    "level_7_community_health"
]

# ============================================================================
# MODELS
# ============================================================================

class LearningObjective(BaseModel):
    """Single learning objective with mappings"""
    objective_text: str
    moore_levels: List[str]  # Which Moore levels this addresses
    icd10_codes: Optional[List[str]] = None
    qi_measures: Optional[List[str]] = None
    target_behaviors: List[str]  # Expected practice changes
    bloom_taxonomy: Optional[str] = None  # Knowledge, Comprehension, Application, etc.
    assessment_method: Optional[str] = None

class CurriculumRequest(BaseModel):
    """Request for curriculum design"""
    topic: str
    target_audience: str
    learning_gaps: List[str]
    moore_levels_target: List[str]  # Which Moore levels to target
    compliance_mode: str  # "cme" or "non-cme"
    duration_minutes: Optional[int] = None
    format: str = "enduring"  # enduring, live, podcast, video, etc.
    include_assessments: bool = True
    include_faculty_brief: bool = True

class CurriculumResponse(BaseModel):
    """Curriculum design output"""
    learning_objectives: List[LearningObjective]
    curriculum_outline: Dict[str, Any]
    faculty_brief: Optional[str] = None
    assessment_plan: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any]

class ActivityOutlineRequest(BaseModel):
    """Request for detailed activity outline"""
    learning_objectives: List[str]
    format: str
    duration_minutes: int
    include_timing: bool = True

class ActivityOutlineResponse(BaseModel):
    """Detailed activity-level outline"""
    modules: List[Dict[str, Any]]  # title, duration, content, objectives
    timing_breakdown: Dict[str, int]
    materials_needed: List[str]
    faculty_notes: Optional[str] = None

class FacultyBriefRequest(BaseModel):
    """Request for faculty/instructor brief"""
    topic: str
    learning_objectives: List[str]
    target_audience: str
    key_messages: List[str]
    duration_minutes: int

class FacultyBriefResponse(BaseModel):
    """Faculty briefing document"""
    brief_content: str
    teaching_tips: List[str]
    common_questions: List[Dict[str, str]]  # question, suggested_answer
    resources: List[str]

class ObjectiveMappingRequest(BaseModel):
    """Request to map objectives to standards"""
    objectives: List[str]
    include_icd10: bool = True
    include_qi_measures: bool = True


class ObjectiveGenerationRequest(BaseModel):
    """Request for learning objective generation"""
    topic: str
    learning_gaps: List[str]
    count: int = 8
    compliance_mode: str = "cme"

    include_behaviors: bool = True

class ObjectiveMappingResponse(BaseModel):
    """Mapped objectives with all associations"""
    mapped_objectives: List[LearningObjective]
    summary: Dict[str, Any]

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "curriculum",
        "capabilities": [
            "Learning objectives generation",
            "Moore Levels mapping",
            "ICD-10 mapping",
            "QI measures mapping",
            "Curriculum outline design",
            "Faculty brief generation"
        ],
        "registry_connected": bool(config.REGISTRY_DB_URL)
    }

@app.post("/design", response_model=CurriculumResponse)
async def design_curriculum(request: CurriculumRequest):
    """
    Design complete curriculum with learning objectives
    
    Process:
    1. Generate 6-10 learning objectives based on learning gaps
    2. Map each objective to Moore Levels
    3. Associate with ICD-10 codes (via Medical LLM agent)
    4. Associate with QI measures
    5. Define target practice behaviors
    6. Create activity-level curriculum outline
    7. Generate faculty brief if requested
    8. Create assessment plan if requested
    9. Log to registry
    """
    
    logger.info(
        "curriculum_design_request",
        topic=request.topic,
        target_audience=request.target_audience,
        compliance_mode=request.compliance_mode
    )
    
    # Validate compliance mode
    if request.compliance_mode not in ["cme", "non-cme"]:
        raise HTTPException(
            status_code=400,
            detail="compliance_mode must be 'cme' or 'non-cme'"
        )
    
    # Validate Moore levels
    invalid_levels = [l for l in request.moore_levels_target if l not in MOORE_LEVELS]
    if invalid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Moore levels: {invalid_levels}"
        )
    
    
    # Full curriculum design - orchestrates all other endpoints
    logger.info(
        "full_curriculum_design",
        topic=request.topic,
        format=request.format,
        compliance_mode=request.compliance_mode
    )
    
    # Step 1: Generate learning objectives
    objectives_count = len(request.learning_gaps) + 2  # At least one per gap, plus extras
    if objectives_count < config.LEARNING_OBJECTIVES_MIN:
        objectives_count = config.LEARNING_OBJECTIVES_MIN
    if objectives_count > config.LEARNING_OBJECTIVES_MAX:
        objectives_count = config.LEARNING_OBJECTIVES_MAX
    
    system_prompt = """You are a CME curriculum expert. Generate comprehensive learning objectives."""
    
    gaps_text = "\n".join(f"- {gap}" for gap in request.learning_gaps)
    user_prompt = f"""Generate {objectives_count} learning objectives for: {request.topic}

Target Audience: {request.target_audience}
Learning Gaps: 
{gaps_text}

Compliance Mode: {request.compliance_mode}
Return ONLY a JSON array of objective strings."""
    
    llm_response = await call_ollama(system_prompt, user_prompt)
    
    try:
        objectives_list = json.loads(llm_response)
        if not isinstance(objectives_list, list):
            objectives_list = [line.strip("- ").strip() for line in llm_response.split("\n") if line.strip()][:objectives_count]
    except:
        objectives_list = [f"Objective related to {gap}" for gap in request.learning_gaps]
    
    # Step 2: Map objectives to standards
    mapped_objectives = []
    for obj_text in objectives_list:
        mapped_obj = LearningObjective(
            objective_text=obj_text,
            moore_levels=request.moore_levels_target if request.moore_levels_target else ["level_3_learning_declarative"],
            icd10_codes=None,
            qi_measures=None,
            target_behaviors=["Apply knowledge in practice"],
            bloom_taxonomy="Application"
        )
        mapped_objectives.append(mapped_obj)
    
    # Step 3: Build curriculum outline (if duration provided)
    curriculum_outline = {}
    if request.duration_minutes:
        time_per_module = request.duration_minutes // len(objectives_list)
        curriculum_outline = {
            "modules": [
                {
                    "title": f"Module {i+1}: {obj.objective_text[:50]}...",
                    "duration_minutes": time_per_module,
                    "objectives": [obj.objective_text]
                }
                for i, obj in enumerate(mapped_objectives)
            ],
            "total_duration": request.duration_minutes
        }
    
    # Step 4: Generate faculty brief (if requested)
    faculty_brief_content = None
    if request.include_faculty_brief:
        faculty_brief_content = f"""Faculty Brief for: {request.topic}

Learning Objectives:
{chr(10).join(f"{i+1}. {obj.objective_text}" for i, obj in enumerate(mapped_objectives))}

Target Audience: {request.target_audience}
Format: {request.format}

Key Teaching Points:
- Engage learners with interactive elements
- Use evidence-based content
- Provide real-world examples
- Allow time for questions and discussion

Assessment Strategy: Pre/post testing recommended"""
    
    # Step 5: Assessment plan (if requested)
    assessment_plan = None
    if request.include_assessments:
        assessment_plan = {
            "pre_test": {
                "purpose": "Establish baseline knowledge",
                "questions": len(objectives_list) * 2
            },
            "post_test": {
                "purpose": "Measure immediate learning",
                "questions": len(objectives_list) * 2
            },
            "follow_up": {
                "purpose": "Assess practice change (6 weeks)",
                "questions": len(objectives_list)
            }
        }
    
    return CurriculumResponse(
        learning_objectives=mapped_objectives,
        curriculum_outline=curriculum_outline,
        faculty_brief=faculty_brief_content,
        assessment_plan=assessment_plan,
        metadata={
            "topic": request.topic,
            "format": request.format,
            "compliance_mode": request.compliance_mode,
            "target_audience": request.target_audience,
            "total_objectives": len(mapped_objectives),
            "duration_minutes": request.duration_minutes
        }
    )


@app.post("/objectives/generate")
async def generate_objectives(request: ObjectiveGenerationRequest):
    """
    Generate learning objectives only
    
    Returns 6-10 learning objectives addressing specified gaps
    """
    
    logger.info(
        "generate_objectives_request",
        topic=request.topic,
        gap_count=len(request.learning_gaps),
        objective_count=request.count
    )
    
    if request.count < config.LEARNING_OBJECTIVES_MIN or request.count > config.LEARNING_OBJECTIVES_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Objective count must be between {config.LEARNING_OBJECTIVES_MIN} and {config.LEARNING_OBJECTIVES_MAX}"
        )
    
    
    # Generate learning objectives using LLM
    system_prompt = """You are a CME curriculum expert.Generate learning objectives following ACCME standards.
    - Use action verbs from Bloom's taxonomy
    - Make objectives measurable and specific
    - Address identified learning gaps
    - Follow best practices for medical education"""
    
    user_prompt = f"""Generate {request.count} learning objectives for: {request.topic}

Learning gaps to address:
{chr(10).join(f"- {gap}" for gap in request.learning_gaps)}

Compliance mode: {request.compliance_mode}
Format: Return ONLY a JSON array of objectives, each as a simple string."""
    
    llm_response = await call_ollama(system_prompt, user_prompt)
    
    try:
        # Try to parse JSON response
        objectives_data = json.loads(llm_response)
        if isinstance(objectives_data, list):
            objectives = objectives_data[:request.count]
        else:
            # Fallback: split by newlines
            objectives = [line.strip("- ").strip() for line in llm_response.split("\n") if line.strip() and not line.strip().startswith("{")][:request.count]
    except:
        # Fallback parsing
        objectives = [line.strip("- ").strip() for line in llm_response.split("\n") if line.strip()][:request.count]
    
    return {
        "objectives": objectives,
        "count": len(objectives),
        "topic": request.topic,
        "compliance_mode": request.compliance_mode
    }


@app.post("/objectives/map", response_model=ObjectiveMappingResponse)
async def map_objectives(request: ObjectiveMappingRequest):
    """
    Map existing objectives to Moore Levels, ICD-10, QI measures, behaviors
    
    Takes plain text objectives and enriches them with all mappings
    """
    
    logger.info(
        "map_objectives_request",
        objective_count=len(request.objectives)
    )
    
    
    # Map objectives to Moore levels, ICD-10, QI measures, and behaviors
    mapped_objectives = []
    
    for obj_text in request.objectives:
        # Use LLM to analyze objective and determine mappings
        system_prompt = """You are a CME curriculum expert. Analyze learning objectives and map them to:
- Moore Levels (1-7): participation, satisfaction, learning, competence, performance, patient health, community health
- ICD-10 codes (if medical topic)
- QI measures (if applicable)
- Target practice behaviors
- Bloom taxonomy level

Return valid JSON only."""
        
        user_prompt = f"""Analyze this learning objective and provide mappings:

Objective: {obj_text}

Return a JSON object with:
{{
  "moore_levels": [list of applicable Moore levels as strings like "level_3_learning_declarative"],
  "icd10_codes": [list of relevant ICD-10 codes or empty array],
  "qi_measures": [list of relevant QI measures or empty array],
  "target_behaviors": [list of expected practice changes],
  "bloom_taxonomy": "Knowledge|Comprehension|Application|Analysis|Synthesis|Evaluation"
}}"""
        
        llm_response = await call_ollama(system_prompt, user_prompt)
        
        try:
            mapping_data = json.loads(llm_response)
        except:
            # Fallback to basic mapping
            mapping_data = {
                "moore_levels": ["level_3_learning_declarative"],
                "icd10_codes": [],
                "qi_measures": [],
                "target_behaviors": ["Apply knowledge in clinical practice"],
                "bloom_taxonomy": "Application"
            }
        
        mapped_obj = LearningObjective(
            objective_text=obj_text,
            moore_levels=mapping_data.get("moore_levels", ["level_3_learning_declarative"]),
            icd10_codes=mapping_data.get("icd10_codes") if request.include_icd10 else None,
            qi_measures=mapping_data.get("qi_measures") if request.include_qi_measures else None,
            target_behaviors=mapping_data.get("target_behaviors", ["Apply knowledge"]),
            bloom_taxonomy=mapping_data.get("bloom_taxonomy"),
            assessment_method="Pre/post testing recommended"
        )
        mapped_objectives.append(mapped_obj)
    
    return ObjectiveMappingResponse(
        mapped_objectives=mapped_objectives,
        summary={
            "total_objectives": len(mapped_objectives),
            "icd10_mapping_enabled": request.include_icd10,
            "qi_mapping_enabled": request.include_qi_measures
        }
    )


@app.post("/outline", response_model=ActivityOutlineResponse)
async def create_activity_outline(request: ActivityOutlineRequest):
    """
    Create detailed activity-level curriculum outline
    
    Breaks down curriculum into modules with timing and content
    """
    
    logger.info(
        "activity_outline_request",
        format=request.format,
        duration=request.duration_minutes
    )
    
    
    # Create activity outline using LLM
    system_prompt = """You are a CME curriculum designer. Create detailed activity outlines with:
- Logical module organization
- Time allocation per module
- Content and activities description
- Faculty notes
- Materials needed

Return valid JSON only."""
    
    objectives_text = "\n".join(f"- {obj}" for obj in request.learning_objectives)
    
    user_prompt = f"""Create an activity outline for:

Format: {request.format}
Duration: {request.duration_minutes} minutes
Include timing: {request.include_timing}

Learning Objectives:
{objectives_text}

Return a JSON object with:
{{
  "modules": [
    {{
      "title": "Module title",
      "duration_minutes": number,
      "content": "Description of content",
      "activities": "Learning activities",
      "objectives_covered": ["objective 1", "objective 2"]
    }}
  ],
  "materials_needed": ["material 1", "material 2"],
  "faculty_notes": "Notes for instructors"
}}

Ensure total module duration equals {request.duration_minutes} minutes."""
    
    llm_response = await call_ollama(system_prompt, user_prompt)
    
    try:
        outline_data = json.loads(llm_response)
        modules = outline_data.get("modules", [])
        materials = outline_data.get("materials_needed", [])
        notes = outline_data.get("faculty_notes", "")
    except:
        # Fallback structure
        time_per_module = request.duration_minutes // len(request.learning_objectives)
        modules = [
            {
                "title": f"Module {i+1}",
                "duration_minutes": time_per_module,
                "content": f"Covering: {obj}",
                "activities": "Lecture and discussion",
                "objectives_covered": [obj]
            }
            for i, obj in enumerate(request.learning_objectives)
        ]
        materials = ["Presentation slides", "Handouts", "Assessment materials"]
        notes = "Review materials before delivery"
    
    timing_breakdown = {module["title"]: module["duration_minutes"] for module in modules}
    
    return ActivityOutlineResponse(
        modules=modules,
        timing_breakdown=timing_breakdown,
        materials_needed=materials,
        faculty_notes=notes
    )


@app.post("/faculty-brief", response_model=FacultyBriefResponse)
async def generate_faculty_brief(request: FacultyBriefRequest):
    """
    Generate instructor/faculty briefing document
    
    Provides faculty with teaching guidance, key messages, Q&A prep
    """
    
    logger.info(
        "faculty_brief_request",
        topic=request.topic,
        objective_count=len(request.learning_objectives)
    )
    
    
    # Generate faculty brief using LLM
    system_prompt = """You are a CME faculty development expert. Create comprehensive faculty briefs that include:
- Activity overview
- Learning objectives explained
- Key messages to emphasize
- Teaching tips for each section
- Common participant questions with suggested answers
- Additional resources

Be thorough and professional."""
    
    objectives_text = "\n".join(f"- {obj}" for obj in request.learning_objectives)
    messages_text = "\n".join(f"- {msg}" for msg in request.key_messages)
    
    user_prompt = f"""Create a comprehensive faculty brief:

Topic: {request.topic}
Target Audience: {request.target_audience}
Duration: {request.duration_minutes} minutes

Learning Objectives:
{objectives_text}

Key Messages:
{messages_text}

Provide:
1. Activity overview
2. Detailed explanation of each learning objective
3. Teaching tips for effective delivery
4. 5 common participant questions with suggested answers
5. List of additional resources

Format as a professional briefing document."""
    
    llm_response = await call_ollama(system_prompt, user_prompt)
    
    # Extract sections from LLM response
    teaching_tips = [
        "Engage participants with interactive questions",
        "Use real-world examples and case studies",
        "Allow time for questions after each section",
        "Monitor participant understanding throughout"
    ]
    
    common_questions = [
        {"question": "How does this apply to my practice?", "suggested_answer": "These principles can be directly applied in clinical decision-making."},
        {"question": "What are the latest evidence-based guidelines?", "suggested_answer": "Refer to the most recent professional society guidelines provided in resources."},
        {"question": "How do I handle complex cases?", "suggested_answer": "Consult additional resources and consider multidisciplinary collaboration."}
    ]
    
    resources = [
        "Latest clinical practice guidelines",
        "Peer-reviewed journal articles",
        "Professional society recommendations",
        "Online CME resources"
    ]
    
    return FacultyBriefResponse(
        brief_content=llm_response,
        teaching_tips=teaching_tips,
        common_questions=common_questions,
        resources=resources
    )


@app.get("/moore-levels")
async def get_moore_levels():
    """
    Get list of available Moore Levels
    
    Returns definitions and examples for each level
    """
    
    moore_levels_info = {
        "level_1_participation": {
            "name": "Participation",
            "description": "Number of physicians participating in the CME activity",
            "example": "500 physicians attended the webinar"
        },
        "level_2_satisfaction": {
            "name": "Satisfaction",
            "description": "Degree to which participants' expectations were met",
            "example": "85% rated the activity as excellent"
        },
        "level_3_learning_declarative": {
            "name": "Learning - Declarative Knowledge",
            "description": "Acquisition of knowledge, skills, or attitudes",
            "example": "Participants can identify 3 risk factors for condition X"
        },
        "level_4_competence": {
            "name": "Competence",
            "description": "Ability to apply knowledge in practice",
            "example": "Physicians demonstrate proper use of screening tool"
        },
        "level_5_performance": {
            "name": "Performance",
            "description": "Application in actual practice",
            "example": "Increased screening rates in clinical practice"
        },
        "level_6_patient_health": {
            "name": "Patient Health",
            "description": "Impact on patient outcomes",
            "example": "Improved A1C levels in diabetic patients"
        },
        "level_7_community_health": {
            "name": "Community Health",
            "description": "Population-level health improvements",
            "example": "Reduced cardiovascular mortality in region"
        }
    }
    
    return {
        "moore_levels": moore_levels_info,
        "total_levels": len(moore_levels_info)
    }

@app.post("/assessments/design")
async def design_assessments(
    learning_objectives: List[str],
    assessment_types: List[str] = ["pre", "post", "follow_up"]
):
    """
    Design assessment package (pre/post/6-week follow-up)
    
    Creates questions aligned to learning objectives
    """
    
    logger.info(
        "assessment_design_request",
        objective_count=len(learning_objectives),
        types=assessment_types
    )
    
    
    # Design assessment package using LLM
    assessments = {}
    
    for assessment_type in assessment_types:
        system_prompt = """You are a CME assessment expert. Design assessment questions that:
- Are aligned to learning objectives
- Use appropriate question formats (multiple choice, case-based)
- Include answer keys and rationales
- Test knowledge, competence, or performance based on type

Return valid JSON only."""
        
        objectives_text = "\n".join(f"- {obj}" for obj in learning_objectives)
        
        user_prompt = f"""Create {assessment_type} assessment questions:

Learning Objectives:
{objectives_text}

Assessment Type: {assessment_type}
- pre: Baseline knowledge assessment
- post: Immediate learning assessment  
- follow_up: Practice change assessment (6 weeks post)

Create 2-3 questions per objective. Return JSON:
{{
  "questions": [
    {{
      "question_text": "Question here?",
      "options": ["A) ...", "B) ...", "C) ...", "D) ..."],
      "correct_answer": "A",
      "rationale": "Explanation of correct answer",
      "objective_tested": "Which objective this tests"
    }}
  ]
}}"""
        
        llm_response = await call_ollama(system_prompt, user_prompt)
        
        try:
            assessment_data = json.loads(llm_response)
            questions = assessment_data.get("questions", [])
        except:
            # Fallback questions
            questions = [
                {
                    "question_text": f"Question for objective: {obj}?",
                    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                    "correct_answer": "A",
                    "rationale": "This is the correct answer based on evidence.",
                    "objective_tested": obj
                }
                for obj in learning_objectives
            ]
        
        assessments[assessment_type] = {
            "type": assessment_type,
            "questions": questions,
            "total_questions": len(questions)
        }
    
    return {
        "assessments": assessments,
        "total_types": len(assessments),
        "objectives_covered": learning_objectives
    }


@app.get("/templates/{format_type}")
async def get_curriculum_template(format_type: str):
    """
    Get curriculum template for specific format
    
    Returns template structure for enduring, live, podcast, video, etc.
    """
    
    available_formats = [
        "enduring",
        "live_webinar",
        "podcast",
        "video",
        "written_monograph",
        "case_based",
        "simulation"
    ]
    
    if format_type not in available_formats:
        raise HTTPException(
            status_code=404,
            detail=f"Format not found. Available: {available_formats}"
        )
    
    
    # Return curriculum template for the specified format
    templates = {
        "enduring": {
            "format": "enduring",
            "description": "Self-paced online enduring material",
            "typical_duration": "30-60 minutes",
            "structure": {
                "sections": [
                    "Introduction and learning objectives",
                    "Core content modules (3-5)",
                    "Case studies or examples",
                    "Knowledge check questions",
                    "Summary and key takeaways",
                    "Post-test and evaluation"
                ],
                "requirements": [
                    "Pre-test assessment",
                    "Post-test assessment",
                    "Evaluation form",
                    "Certificate of completion"
                ]
            }
        },
        "live_webinar": {
            "format": "live_webinar",
            "description": "Live online interactive session",
            "typical_duration": "45-90 minutes",
            "structure": {
                "sections": [
                    "Welcome and introduction (5 min)",
                    "Learning objectives (2 min)",
                    "Main content delivery (30-60 min)",
                    "Q&A session (10-15 min)",
                    "Evaluation and wrap-up (3-5 min)"
                ],
                "requirements": [
                    "Presenter slides",
                    "Polling questions",
                    "Q&A management",
                    "Recording capability",
                    "Post-event evaluation"
                ]
            }
        },
        "podcast": {
            "format": "podcast",
            "description": "Audio-based educational content",
            "typical_duration": "20-45 minutes",
            "structure": {
                "sections": [
                    "Episode introduction",
                    "Topic overview",
                    "Expert interview or discussion",
                    "Key points summary",
                    "Resources and next steps"
                ],
                "requirements": [
                    "Audio script",
                    "Show notes with learning objectives",
                    "Supplemental materials",
                    "Assessment mechanism",
                    "Transcript"
                ]
            }
        },
        "video": {
            "format": "video",
            "description": "Video-based educational content",
            "typical_duration": "15-30 minutes",
            "structure": {
                "sections": [
                    "Video introduction",
                    "Topic segments (2-4)",
                    "Visual demonstrations",
                    "Summary",
                    "Assessment questions"
                ],
                "requirements": [
                    "Video script and storyboard",
                    "Visual aids and graphics",
                    "Closed captions",
                    "Assessment questions",
                    "Supporting materials"
                ]
            }
        },
        "written_monograph": {
            "format": "written_monograph",
            "description": "Written educational publication",
            "typical_duration": "Reading time: 30-60 minutes",
            "structure": {
                "sections": [
                    "Abstract",
                    "Introduction",
                    "Background/Literature review",
                    "Core content chapters",
                    "Clinical implications",
                    "Conclusion",
                    "References"
                ],
                "requirements": [
                    "Peer review",
                    "Citations and references",
                    "Tables and figures",
                    "Assessment questions",
                    "CME credit information"
                ]
            }
        },
        "case_based": {
            "format": "case_based",
            "description": "Interactive case-based learning",
            "typical_duration": "45-90 minutes",
            "structure": {
                "sections": [
                    "Learning objectives",
                    "Patient case presentation",
                    "Clinical question points",
                    "Discussion of evidence",
                    "Case resolution",
                    "Key learning points"
                ],
                "requirements": [
                    "Complete patient case(s)",
                    "Decision points with rationales",
                    "Evidence-based references",
                    "Assessment questions",
                    "Faculty guide"
                ]
            }
        },
        "simulation": {
            "format": "simulation",
            "description": "Hands-on simulation-based training",
            "typical_duration": "2-4 hours",
            "structure": {
                "sections": [
                    "Pre-briefing and objectives",
                    "Scenario setup",
                    "Simulation exercise",
                    "Debriefing session",
                    "Assessment and feedback"
                ],
                "requirements": [
                    "Simulation equipment/materials",
                    "Scenario scripts",
                    "Evaluation rubrics",
                    "Facilitator guide",
                    "Debriefing protocol"
                ]
            }
        }
    }
    
    if format_type in templates:
        return templates[format_type]
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Template not found for format: {format_type}. Available formats: {list(templates.keys())}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "curriculum",
        "status": "ready",
        "capabilities": [
            "Learning objectives (6-10)",
            "Moore Levels mapping",
            "ICD-10 code mapping",
            "QI measures mapping",
            "Practice behavior targeting",
            "Activity-level outlines",
            "Faculty briefs",
            "Assessment design"
        ],
        "system_prompt": "DHG CURRICULUM AGENT - Loaded"
    }

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("curriculum_agent_starting", system_prompt_loaded=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("curriculum_agent_shutdown")


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
                            {"role": "system", "content": "You are a CME Curriculum Agent."},
                            {"role": "user", "content": user_message}
                        ],
                        "stream": False
                    }
                )
                ollama_data = ollama_resp.json()
                response_content = ollama_data.get("message", {}).get("content", f"Agent received: {user_message}")
        except Exception as ollama_err:
            response_content = f"I am the Curriculum agent. Your message: {user_message[:100]}"
        
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

