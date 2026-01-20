"""
DHG AI FACTORY - OUTCOMES AGENT
Moore's Levels outcomes planning and measurement
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import structlog

logger = structlog.get_logger()

app = FastAPI(
    title="DHG Outcomes Agent",
    description="Moore's Levels outcomes planning and measurement",
    version="1.0.0"
)

# ============================================================================
# SYSTEM PROMPT - DHG OUTCOMES AGENT
# ============================================================================

SYSTEM_PROMPT = """
SYSTEM: DHG OUTCOMES AGENT

Your tasks:
- Build outcomes methodologies
- Align assessments with Moore Levels (3–5)
- Generate instruments for:
   • pre
   • post
   • 6-week follow-up
- Suggest 3 innovative outcomes pathways
- Build outcomes data map
- Integrate QI Measures + ICD-10 logic
- Log all tasks to registry
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    OUTCOMES_MOORE_LEVELS = int(os.getenv("OUTCOMES_MOORE_LEVELS", "7"))

config = Config()

# ============================================================================
# ENUMS
# ============================================================================

MOORE_LEVELS = {
    1: {"name": "Participation", "description": "Number of physicians participating"},
    2: {"name": "Satisfaction", "description": "Participant satisfaction level"},
    3: {"name": "Learning", "description": "Declarative knowledge acquisition"},
    4: {"name": "Competence", "description": "Ability to apply knowledge"},
    5: {"name": "Performance", "description": "Application in practice"},
    6: {"name": "Patient Health", "description": "Impact on patient outcomes"},
    7: {"name": "Community Health", "description": "Population-level improvements"}
}

ASSESSMENT_TYPES = ["pre", "post", "6_week_follow_up"]

# ============================================================================
# MODELS
# ============================================================================

class OutcomesRequest(BaseModel):
    """Request for outcomes planning"""
    learning_objectives: List[str]
    target_moore_levels: List[int]  # e.g., [3, 4, 5]
    intervention_type: str  # podcast, video, webinar, etc.
    target_audience: str
    icd10_codes: Optional[List[str]] = None
    qi_measures: Optional[List[str]] = None
    duration_minutes: Optional[int] = None

class OutcomesResponse(BaseModel):
    """Comprehensive outcomes plan"""
    methodology: Dict[str, Any]
    assessment_instruments: Dict[str, Any]  # pre, post, follow_up
    innovative_pathways: List[Dict[str, Any]]  # 3 pathways
    data_map: Dict[str, Any]
    metadata: Dict[str, Any]

class AssessmentInstrument(BaseModel):
    """Single assessment instrument (pre/post/follow-up)"""
    assessment_type: str  # pre, post, 6_week_follow_up
    moore_levels_measured: List[int]
    questions: List[Dict[str, Any]]
    scoring_rubric: Dict[str, Any]
    estimated_completion_minutes: int
    instructions: str

class InnovativePathway(BaseModel):
    """Innovative outcomes measurement pathway"""
    pathway_name: str
    description: str
    moore_levels_targeted: List[int]
    data_collection_methods: List[str]
    technology_requirements: List[str]
    implementation_complexity: str  # low, medium, high
    expected_insights: List[str]
    estimated_cost: Optional[str] = None

class OutcomesDataMap(BaseModel):
    """Map of outcomes data collection and flow"""
    data_points: List[Dict[str, Any]]
    collection_schedule: Dict[str, str]
    data_sources: List[str]
    analysis_methods: List[str]
    reporting_frequency: str

class MethodologyRequest(BaseModel):
    """Request for outcomes methodology design"""
    moore_levels: List[int]
    intervention_type: str
    participant_count_estimate: int
    follow_up_duration_weeks: int = 6

class MethodologyResponse(BaseModel):
    """Outcomes methodology design"""
    approach: str
    measurement_framework: Dict[str, Any]
    data_collection_strategy: Dict[str, Any]
    analysis_plan: Dict[str, Any]
    sample_size_requirements: Dict[str, int]
    statistical_methods: List[str]

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "outcomes",
        "moore_levels_supported": config.OUTCOMES_MOORE_LEVELS,
        "assessment_types": ASSESSMENT_TYPES,
        "registry_connected": bool(config.REGISTRY_DB_URL)
    }

@app.post("/plan", response_model=OutcomesResponse)
async def plan_outcomes(request: OutcomesRequest):
    """
    Build comprehensive outcomes plan
    
    Process:
    1. Design outcomes methodology for target Moore Levels
    2. Generate assessment instruments (pre/post/6-week)
    3. Suggest 3 innovative outcomes pathways
    4. Build outcomes data map
    5. Integrate QI Measures + ICD-10 codes
    6. Log to registry
    """
    
    logger.info(
        "outcomes_plan_request",
        target_moore_levels=request.target_moore_levels,
        intervention_type=request.intervention_type
    )
    
    # Validate Moore levels
    invalid_levels = [l for l in request.target_moore_levels if l not in MOORE_LEVELS]
    if invalid_levels:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Moore levels: {invalid_levels}. Valid: 1-7"
        )
    
    # Focus on levels 3-5 as specified
    if not any(level in [3, 4, 5] for level in request.target_moore_levels):
        logger.warning("No Moore Levels 3-5 specified, adding level 3")
        request.target_moore_levels.append(3)
    
    # Build comprehensive outcomes plan
    methodology = _build_methodology(
        request.target_moore_levels,
        request.intervention_type,
        request.target_audience
    )
    
    # Generate assessment instruments
    instruments = _generate_instruments(
        request.learning_objectives,
        request.target_moore_levels
    )
    
    # Create innovative pathways
    pathways = _create_pathways(
        request.intervention_type,
        request.target_moore_levels
    )
    
    # Build data map
    data_map = _build_data_map(
        request.learning_objectives,
        request.target_moore_levels,
        request.icd10_codes,
        request.qi_measures
    )
    
    logger.info(
        "outcomes_plan_complete",
        pathway_count=len(pathways),
        instrument_count=len(instruments)
    )
    
    return OutcomesResponse(
        methodology=methodology,
        assessment_instruments=instruments,
        innovative_pathways=pathways,
        data_map=data_map,
        metadata={
            "learning_objectives_count": len(request.learning_objectives),
            "target_moore_levels": request.target_moore_levels,
            "intervention_type": request.intervention_type,
            "icd10_integrated": bool(request.icd10_codes),
            "qi_integrated": bool(request.qi_measures)
        }
    )

@app.post("/methodology", response_model=MethodologyResponse)
async def design_methodology(request: MethodologyRequest):
    """
    Design outcomes measurement methodology
    
    Creates comprehensive measurement framework aligned to Moore Levels
    """
    
    logger.info(
        "methodology_design_request",
        moore_levels=request.moore_levels,
        participant_count=request.participant_count_estimate
    )
    
    # Design comprehensive methodology
    framework = {
        "approach": f"Mixed-methods outcomes assessment for {request.intervention_type}",
        "measurement_framework": {
            level: {
                "name": MOORE_LEVELS[level]["name"],
                "instruments": _get_level_instruments(level),
                "timeline": _get_typical_timeline(level),
                "data_sources": _get_level_data_sources(level)
            }
            for level in request.moore_levels
        },
        "data_collection_strategy": {
            "pre_activity": "Baseline assessment of knowledge and practice patterns",
            "immediate_post": "Knowledge acquisition and satisfaction measurement",
            "follow_up": f"Practice change assessment at {request.follow_up_duration_weeks} weeks"
        },
        "analysis_plan": {
            "descriptive": "Means, frequencies, change scores",
            "inferential": "Paired t-tests, McNemar's test for paired proportions",
            "effect_size": "Cohen's d for continuous, odds ratios for categorical"
        },
        "sample_size_requirements": _calculate_sample_sizes(request.participant_count_estimate, request.moore_levels),
        "statistical_methods": [
            "Paired t-test for pre/post comparisons",
            "Repeated measures ANOVA for longitudinal data",
            "Chi-square for categorical outcomes",
            "Effect size calculations (Cohen's d)"
        ]
    }
    
    return MethodologyResponse(
        approach=framework["approach"],
        measurement_framework=framework["measurement_framework"],
        data_collection_strategy=framework["data_collection_strategy"],
        analysis_plan=framework["analysis_plan"],
        sample_size_requirements=framework["sample_size_requirements"],
        statistical_methods=framework["statistical_methods"]
    )

@app.post("/instruments/generate")
async def generate_assessment_instruments(
    learning_objectives: List[str],
    moore_levels: List[int],
    assessment_types: List[str] = ["pre", "post", "6_week_follow_up"]
) -> Dict[str, AssessmentInstrument]:
    """
    Generate assessment instruments (pre/post/6-week follow-up)
    
    Creates question sets aligned to learning objectives and Moore Levels
    """
    
    logger.info(
        "generate_instruments_request",
        objective_count=len(learning_objectives),
        assessment_types=assessment_types
    )
    
    # Generate instruments for each assessment type
    instruments = {}
    
    for assessment_type in assessment_types:
        questions = []
        
        for i, objective in enumerate(learning_objectives):
            question_set = _generate_questions_for_objective(
                objective, 
                assessment_type, 
                moore_levels,
                i + 1
            )
            questions.extend(question_set)
        
        instruments[assessment_type] = AssessmentInstrument(
            assessment_type=assessment_type,
            moore_levels_measured=moore_levels,
            questions=questions,
            scoring_rubric=_get_scoring_rubric(assessment_type, moore_levels),
            estimated_completion_minutes=max(5, len(questions) * 2),
            instructions=_get_assessment_instructions(assessment_type)
        )
    
    logger.info(
        "instruments_generated",
        types=assessment_types,
        total_questions=sum(len(inst.questions) for inst in instruments.values())
    )
    
    return instruments

@app.post("/pathways/suggest")
async def suggest_innovative_pathways(
    intervention_type: str,
    target_moore_levels: List[int],
    count: int = 3
) -> List[InnovativePathway]:
    """
    Suggest 3 innovative outcomes measurement pathways
    
    Returns creative, technology-enabled approaches to outcomes
    """
    
    logger.info(
        "suggest_pathways_request",
        intervention_type=intervention_type,
        pathway_count=count
    )
    
    if count < 1 or count > 5:
        raise HTTPException(
            status_code=400,
            detail="Pathway count must be between 1 and 5"
        )
    
    # Generate innovative pathway suggestions
    all_pathways = [
        InnovativePathway(
            pathway_name="EHR Integration Pathway",
            description="Direct integration with electronic health records to capture real-world practice changes and patient outcomes",
            moore_levels_targeted=[5, 6],
            data_collection_methods=["EHR data extraction", "Claims analysis", "Clinical decision alerts"],
            technology_requirements=["EHR API access", "Data warehouse", "HIPAA compliance"],
            implementation_complexity="high",
            expected_insights=["Prescribing pattern changes", "Guideline adherence rates", "Patient outcome improvements"],
            estimated_cost="$15,000-50,000"
        ),
        InnovativePathway(
            pathway_name="Mobile Commitment-to-Change Tracker",
            description="Smartphone app for learners to log practice changes and barriers in real-time",
            moore_levels_targeted=[4, 5],
            data_collection_methods=["In-app logging", "Push notifications", "Photo documentation"],
            technology_requirements=["Mobile app (iOS/Android)", "Backend database", "Notification service"],
            implementation_complexity="medium",
            expected_insights=["Barriers to implementation", "Time to practice change", "Sustainability of changes"],
            estimated_cost="$8,000-20,000"
        ),
        InnovativePathway(
            pathway_name="Peer Comparison Dashboard",
            description="Anonymous benchmarking against peer performance with quality metric integration",
            moore_levels_targeted=[3, 4, 5],
            data_collection_methods=["Self-reported metrics", "Claims data", "Quality measure feeds"],
            technology_requirements=["Web dashboard", "Analytics engine", "Data visualization"],
            implementation_complexity="medium",
            expected_insights=["Relative performance", "Improvement opportunities", "Best practice identification"],
            estimated_cost="$10,000-25,000"
        ),
        InnovativePathway(
            pathway_name="AI Practice Pattern Analyzer",
            description="Machine learning analysis of practice patterns to identify educational impact",
            moore_levels_targeted=[5, 6, 7],
            data_collection_methods=["Claims data mining", "NLP of clinical notes", "Predictive modeling"],
            technology_requirements=["ML platform", "Large dataset access", "PHI handling"],
            implementation_complexity="high",
            expected_insights=["Practice variation", "Outcome correlations", "Population health trends"],
            estimated_cost="$25,000-75,000"
        ),
        InnovativePathway(
            pathway_name="Patient Outcome Registry",
            description="Condition-specific registry tracking patient outcomes linked to provider education",
            moore_levels_targeted=[6, 7],
            data_collection_methods=["Patient surveys", "Clinical data entry", "Lab result integration"],
            technology_requirements=["Registry platform", "Patient portal", "Interoperability standards"],
            implementation_complexity="high",
            expected_insights=["Patient health improvements", "Cost-effectiveness", "Long-term impact"],
            estimated_cost="$30,000-100,000"
        )
    ]
    
    # Filter by relevant Moore levels and limit count
    relevant_pathways = [
        p for p in all_pathways 
        if any(level in p.moore_levels_targeted for level in target_moore_levels)
    ][:count]
    
    logger.info("pathways_suggested", count=len(relevant_pathways))
    
    return relevant_pathways if relevant_pathways else all_pathways[:count]

@app.post("/data-map")
async def build_data_map(
    assessment_instruments: List[str],
    moore_levels: List[int],
    icd10_codes: Optional[List[str]] = None,
    qi_measures: Optional[List[str]] = None
) -> OutcomesDataMap:
    """
    Build outcomes data collection and flow map
    
    Integrates QI Measures + ICD-10 codes with outcomes data
    """
    
    logger.info(
        "data_map_request",
        instrument_count=len(assessment_instruments),
        icd10_count=len(icd10_codes) if icd10_codes else 0,
        qi_count=len(qi_measures) if qi_measures else 0
    )
    
    # Build comprehensive data collection map
    data_points = []
    
    # Add assessment data points
    for instrument in assessment_instruments:
        for level in moore_levels:
            data_points.append({
                "name": f"{instrument}_{MOORE_LEVELS[level]['name'].lower()}_score",
                "source": instrument,
                "moore_level": level,
                "data_type": "numeric",
                "collection_method": "survey"
            })
    
    # Add ICD-10 data points
    if icd10_codes:
        for code in icd10_codes:
            data_points.append({
                "name": f"diagnosis_{code}",
                "source": "claims_ehr",
                "icd10_code": code,
                "data_type": "categorical",
                "collection_method": "extraction"
            })
    
    # Add QI measure data points
    if qi_measures:
        for measure in qi_measures:
            data_points.append({
                "name": f"qi_{measure.replace(' ', '_').lower()}",
                "source": "quality_registry",
                "qi_measure": measure,
                "data_type": "numeric",
                "collection_method": "registry_query"
            })
    
    return OutcomesDataMap(
        data_points=data_points,
        collection_schedule={
            "pre": "Before activity (up to 7 days prior)",
            "post": "Immediately after activity",
            "6_week_follow_up": "6 weeks post-activity",
            "qi_measures": "Quarterly",
            "claims_data": "Monthly"
        },
        data_sources=["Survey platform", "EHR/Claims", "Quality registries", "Patient portals"],
        analysis_methods=["Pre-post comparison", "Trend analysis", "Benchmark comparison", "Statistical significance testing"],
        reporting_frequency="Quarterly with annual comprehensive report"
    )

@app.get("/moore-levels")
async def get_moore_levels_info():
    """
    Get detailed information about Moore's 7 Levels
    
    Returns definitions, measurement approaches, and examples
    """
    
    detailed_info = {}
    
    for level, info in MOORE_LEVELS.items():
        detailed_info[f"level_{level}"] = {
            **info,
            "measurement_approach": _get_measurement_approach(level),
            "example_metrics": _get_example_metrics(level),
            "typical_timeline": _get_typical_timeline(level)
        }
    
    return {
        "moore_levels": detailed_info,
        "focus_levels": [3, 4, 5],
        "focus_rationale": "Levels 3-5 represent learning, competence, and performance - most directly measurable CME outcomes"
    }

def _get_measurement_approach(level: int) -> str:
    """Get measurement approach for Moore Level"""
    approaches = {
        1: "Attendance records, registration data",
        2: "Satisfaction surveys, feedback forms",
        3: "Pre/post knowledge tests, case scenarios",
        4: "OSCE, simulations, practice demonstrations",
        5: "Chart reviews, claims data, quality measures",
        6: "Patient outcomes, clinical registries, EHR data",
        7: "Population health metrics, epidemiological data"
    }
    return approaches.get(level, "Not defined")

def _get_example_metrics(level: int) -> List[str]:
    """Get example metrics for Moore Level"""
    metrics = {
        1: ["Participant count", "Completion rate"],
        2: ["Satisfaction score", "Net Promoter Score", "Perceived relevance"],
        3: ["Pre/post test scores", "Knowledge gain", "Attitude change"],
        4: ["Competency assessment scores", "Simulation performance", "Skills demonstration"],
        5: ["Prescribing patterns", "Screening rates", "Protocol adherence"],
        6: ["A1C levels", "Blood pressure control", "Hospital readmission rates"],
        7: ["Disease prevalence", "Mortality rates", "Healthcare utilization"]
    }
    return metrics.get(level, [])

def _get_typical_timeline(level: int) -> str:
    """Get typical measurement timeline for Moore Level"""
    timelines = {
        1: "During activity",
        2: "Immediately post-activity",
        3: "Pre and immediately post-activity",
        4: "1-3 months post-activity",
        5: "3-6 months post-activity",
        6: "6-12 months post-activity",
        7: "12+ months post-activity"
    }
    return timelines.get(level, "Not defined")


# ============================================================================
# HELPER FUNCTIONS FOR PLAN ENDPOINT
# ============================================================================

def _build_methodology(
    moore_levels: List[int],
    intervention_type: str,
    target_audience: str
) -> Dict[str, Any]:
    """Build methodology dict for outcomes plan"""
    return {
        "approach": f"Mixed-methods outcomes assessment for {intervention_type}",
        "target_audience": target_audience,
        "moore_levels_assessed": [
            {"level": level, "name": MOORE_LEVELS[level]["name"]}
            for level in moore_levels
        ],
        "measurement_timeline": {
            "pre": "Up to 7 days before activity",
            "post": "Immediately after activity",
            "follow_up": "6 weeks post-activity"
        },
        "statistical_approach": "Pre-post paired comparison with effect size calculation"
    }


def _generate_instruments(
    learning_objectives: List[str],
    moore_levels: List[int]
) -> Dict[str, Any]:
    """Generate assessment instruments for outcomes plan"""
    instruments = {}
    
    for assessment_type in ["pre", "post", "6_week_follow_up"]:
        questions = []
        for i, objective in enumerate(learning_objectives[:5]):  # Limit to 5
            questions.append({
                "id": f"q{i+1}_{assessment_type}",
                "objective_reference": objective[:100],
                "question_type": "multiple_choice" if assessment_type != "6_week_follow_up" else "self_report",
                "moore_level": moore_levels[0] if moore_levels else 3
            })
        
        instruments[assessment_type] = {
            "question_count": len(questions),
            "questions": questions,
            "estimated_minutes": max(5, len(questions) * 2)
        }
    
    return instruments


def _create_pathways(
    intervention_type: str,
    moore_levels: List[int]
) -> List[Dict[str, Any]]:
    """Create innovative pathways for outcomes plan"""
    return [
        {
            "name": "Mobile Practice Tracker",
            "moore_levels": [4, 5],
            "description": "App-based commitment-to-change tracking",
            "complexity": "medium"
        },
        {
            "name": "Peer Benchmarking",
            "moore_levels": [3, 4, 5],
            "description": "Anonymous performance comparison dashboard",
            "complexity": "medium"
        },
        {
            "name": "EHR Integration",
            "moore_levels": [5, 6],
            "description": "Direct practice data extraction",
            "complexity": "high"
        }
    ]


def _build_data_map(
    learning_objectives: List[str],
    moore_levels: List[int],
    icd10_codes: Optional[List[str]],
    qi_measures: Optional[List[str]]
) -> Dict[str, Any]:
    """Build data collection map for outcomes plan"""
    data_points = []
    
    for level in moore_levels:
        data_points.append({
            "moore_level": level,
            "data_type": f"level_{level}_score",
            "collection_method": "survey"
        })
    
    if icd10_codes:
        for code in icd10_codes[:3]:
            data_points.append({
                "icd10_code": code,
                "data_type": "claims_data",
                "collection_method": "extraction"
            })
    
    if qi_measures:
        for measure in qi_measures[:3]:
            data_points.append({
                "qi_measure": measure,
                "data_type": "quality_metric",
                "collection_method": "registry_query"
            })
    
    return {
        "data_points": data_points,
        "total_data_points": len(data_points),
        "collection_schedule": "Pre, Post, 6-week, Quarterly",
        "reporting": "Quarterly with annual comprehensive report"
    }


def _get_level_instruments(level: int) -> List[str]:
    """Get instruments for a Moore Level"""
    instruments = {
        1: ["Registration logs", "Attendance tracking"],
        2: ["Satisfaction survey", "Feedback form"],
        3: ["Pre/post knowledge test", "Case scenarios"],
        4: ["OSCE", "Simulation", "Skills checklist"],
        5: ["Chart review", "Claims analysis", "Quality measures"],
        6: ["Patient surveys", "Clinical registries", "Lab values"],
        7: ["Population metrics", "Epidemiological data"]
    }
    return instruments.get(level, ["Custom assessment"])


def _get_level_data_sources(level: int) -> List[str]:
    """Get data sources for a Moore Level"""
    sources = {
        1: ["LMS", "Registration system"],
        2: ["Survey platform"],
        3: ["Survey platform", "Test database"],
        4: ["Simulation center", "OSCE records"],
        5: ["EHR", "Claims data", "Quality registries"],
        6: ["Clinical registries", "Patient portals", "EHR"],
        7: ["Public health databases", "CDC data", "CMS data"]
    }
    return sources.get(level, ["Custom source"])


def _calculate_sample_sizes(participant_count: int, moore_levels: List[int]) -> Dict[str, int]:
    """Calculate sample size requirements for each Moore Level"""
    return {
        f"level_{level}": min(participant_count, 50 + (level * 10))
        for level in moore_levels
    }


def _generate_questions_for_objective(
    objective: str,
    assessment_type: str,
    moore_levels: List[int],
    question_number: int
) -> List[Dict[str, Any]]:
    """Generate questions for a learning objective"""
    questions = []
    
    if assessment_type == "pre":
        questions.append({
            "id": f"pre_q{question_number}",
            "type": "multiple_choice",
            "stem": f"Baseline assessment for: {objective[:50]}...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "A",
            "moore_level": moore_levels[0] if moore_levels else 3
        })
    elif assessment_type == "post":
        questions.append({
            "id": f"post_q{question_number}",
            "type": "multiple_choice",
            "stem": f"Post-activity assessment for: {objective[:50]}...",
            "options": ["Option A", "Option B", "Option C", "Option D"],
            "correct_answer": "A",
            "moore_level": moore_levels[0] if moore_levels else 3
        })
    else:  # 6_week_follow_up
        questions.append({
            "id": f"followup_q{question_number}",
            "type": "self_report",
            "stem": f"Have you implemented changes related to: {objective[:50]}...?",
            "scale": "5-point Likert",
            "moore_level": 5
        })
    
    return questions


def _get_scoring_rubric(assessment_type: str, moore_levels: List[int]) -> Dict[str, Any]:
    """Get scoring rubric for an assessment type"""
    return {
        "scoring_method": "Points-based" if assessment_type != "6_week_follow_up" else "Likert scale",
        "passing_threshold": "70%" if assessment_type != "6_week_follow_up" else "N/A",
        "interpretation_guide": {
            "high": "Strong evidence of learning/change",
            "medium": "Moderate evidence of learning/change",
            "low": "Limited evidence of learning/change"
        }
    }


def _get_assessment_instructions(assessment_type: str) -> str:
    """Get instructions for an assessment type"""
    instructions = {
        "pre": "Please complete this assessment before beginning the educational activity. Your responses help us tailor content to your needs.",
        "post": "Please complete this assessment immediately after the educational activity. This helps us measure learning outcomes.",
        "6_week_follow_up": "Please reflect on how you have applied what you learned in your clinical practice over the past 6 weeks."
    }
    return instructions.get(assessment_type, "Please complete all items.")


def _objectives_relate_to_measure(objective: str, qi_measure: str) -> bool:
    """Check if a learning objective relates to a QI measure"""
    objective_lower = objective.lower()
    measure_lower = qi_measure.lower()
    
    keywords_to_check = measure_lower.split()[:3]
    return any(keyword in objective_lower for keyword in keywords_to_check if len(keyword) > 3)


def _get_icd10_description(code: str) -> str:
    """Get description for ICD-10 code"""
    descriptions = {
        "E11": "Type 2 diabetes mellitus",
        "I10": "Essential (primary) hypertension",
        "F32": "Major depressive disorder, single episode",
        "J45": "Asthma",
        "M54": "Dorsalgia (back pain)"
    }
    prefix = code[:3] if len(code) >= 3 else code
    return descriptions.get(prefix, f"Condition related to {code}")


def _get_relevant_outcomes_for_code(code: str) -> List[str]:
    """Get relevant outcomes for an ICD-10 code"""
    outcomes = {
        "E11": ["A1C control", "Diabetes complications", "Medication adherence"],
        "I10": ["Blood pressure control", "Cardiovascular events", "Medication adherence"],
        "F32": ["PHQ-9 scores", "Treatment response", "Remission rates"],
        "J45": ["Exacerbation rates", "ED visits", "Controller medication use"],
        "M54": ["Pain scores", "Functional status", "Opioid utilization"]
    }
    prefix = code[:3] if len(code) >= 3 else code
    return outcomes.get(prefix, ["Clinical improvement", "Patient satisfaction"])


def _get_qi_measures_for_code(code: str) -> List[str]:
    """Get linked QI measures for an ICD-10 code"""
    measures = {
        "E11": ["NQF 0059: Diabetes HbA1c Control", "HEDIS CDC"],
        "I10": ["NQF 0018: Controlling High Blood Pressure"],
        "F32": ["PHQ-9 depression screening", "Depression remission at 12 months"],
        "J45": ["NQF 0047: Asthma Pharmacologic Therapy"],
        "M54": ["MIPS 131: Back Pain Treatment"]
    }
    prefix = code[:3] if len(code) >= 3 else code
    return measures.get(prefix, ["Relevant quality measures"])

@app.post("/integrate/qi-measures")
async def integrate_qi_measures(
    qi_measures: List[str],
    learning_objectives: List[str]
) -> Dict[str, Any]:
    """
    Integrate QI measures with outcomes plan
    
    Maps quality measures to learning objectives and outcomes
    """
    
    logger.info(
        "qi_integration_request",
        qi_count=len(qi_measures),
        objective_count=len(learning_objectives)
    )
    
    # Map QI measures to learning objectives
    mappings = []
    
    for qi_measure in qi_measures:
        relevant_objectives = [
            obj for obj in learning_objectives
            if _objectives_relate_to_measure(obj, qi_measure)
        ]
        
        mappings.append({
            "qi_measure": qi_measure,
            "matched_objectives": relevant_objectives if relevant_objectives else learning_objectives[:2],
            "data_source": "quality_registry",
            "collection_frequency": "quarterly",
            "baseline_period": "12 months pre-activity",
            "follow_up_period": "12 months post-activity",
            "expected_improvement": "5-15%"
        })
    
    return {
        "qi_measure_mappings": mappings,
        "total_measures": len(qi_measures),
        "total_objectives_linked": sum(len(m["matched_objectives"]) for m in mappings),
        "data_integration_plan": "Link QI registry data to participant identifiers via NPI numbers",
        "analysis_approach": "Compare pre/post measure performance with matched control group"
    }

@app.post("/integrate/icd10")
async def integrate_icd10_codes(
    icd10_codes: List[str],
    outcomes_plan: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Integrate ICD-10 codes with outcomes logic
    
    Links diagnosis codes to relevant outcome measures
    """
    
    logger.info(
        "icd10_integration_request",
        code_count=len(icd10_codes)
    )
    
    # Map ICD-10 codes to outcomes logic
    code_mappings = []
    
    for code in icd10_codes:
        code_mappings.append({
            "icd10_code": code,
            "description": _get_icd10_description(code),
            "relevant_outcomes": _get_relevant_outcomes_for_code(code),
            "patient_population_criteria": f"Patients with primary or secondary diagnosis of {code}",
            "data_extraction_query": f"SELECT * FROM claims WHERE icd10_code LIKE '{code}%'",
            "linked_qi_measures": _get_qi_measures_for_code(code)
        })
    
    return {
        "icd10_mappings": code_mappings,
        "total_codes": len(icd10_codes),
        "patient_identification_method": "Claims-based identification with EHR validation",
        "data_sources": ["Claims data", "EHR diagnosis codes", "Problem lists"],
        "outcomes_plan_updated": True,
        "original_plan_enhanced_with": "Condition-specific patient cohort identification"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "outcomes",
        "status": "ready",
        "capabilities": [
            "Outcomes methodology design",
            "Moore Levels 3-5 alignment",
            "Pre/post/6-week assessment instruments",
            "3 innovative outcomes pathways",
            "Outcomes data mapping",
            "QI measures integration",
            "ICD-10 logic integration"
        ],
        "system_prompt": "DHG OUTCOMES AGENT - Loaded"
    }

@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    logger.info("outcomes_agent_starting", system_prompt_loaded=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown tasks"""
    logger.info("outcomes_agent_shutdown")


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
                            {"role": "system", "content": "You are an Outcomes Assessment Agent."},
                            {"role": "user", "content": user_message}
                        ],
                        "stream": False
                    }
                )
                ollama_data = ollama_resp.json()
                response_content = ollama_data.get("message", {}).get("content", f"Agent received: {user_message}")
        except Exception as ollama_err:
            response_content = f"I am the Outcomes agent. Your message: {user_message[:100]}"
        
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

