import os
#!/usr/bin/env python3
"""
Run all CME agents for multiple disease topics with logging.
Saves outputs to scaffolded folder structure with detailed run log.
"""

import json
import httpx
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# =============================================================================
# CONFIGURATION
# =============================================================================

LANGGRAPH_URL = "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app"
API_KEY = os.environ.get("LANGGRAPH_API_KEY", "")
OUTPUT_DIR = Path("/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/outputs")

AGENTS = [
    "learning_objectives",
    "curriculum_design", 
    "research_protocol",
    "marketing_plan",
    "grant_writer",
    "compliance_review"
]

DOCUMENT_FIELDS = {
    "learning_objectives": "learning_objectives_document",
    "curriculum_design": "curriculum_document",
    "research_protocol": "protocol_document",
    "marketing_plan": "marketing_document",
    "grant_writer": "grant_document",
    "compliance_review": "compliance_report",
}

# =============================================================================
# DISEASE TOPICS WITH FULL INPUT DATA
# =============================================================================

TOPICS = {
    "1_hfpef": {
        "disease_state": "heart failure with preserved ejection fraction",
        "therapeutic_area": "cardiology",
        "target_audience": "cardiologists",
        "estimated_reach": 500,
        "marketing_budget": 75000,
        "moore_level_target": "Level 5",
        "educational_format": "webinar",
        "duration_minutes": 90,
        "modality": "hybrid",
        "practice_settings": ["hospital", "outpatient cardiology"],
        "project_title": "Optimizing HFpEF Care: From Guidelines to Practice",
        "activity_title": "HFpEF Management Webinar Series",
        "supporter_company": "CardioPharm Inc",
        "supporter_products": ["Farxiga", "Brilinta"],
        "competitor_products": ["Jardiance", "Entresto"],
        "gaps": [
            {"gap_id": "GAP-001", "title": "Underutilization of SGLT2 inhibitors in HFpEF", 
             "root_causes": {"primary_barrier_type": "knowledge", "contributing_factors": ["Confusing guidelines", "Insurance prior auth"]}},
            {"gap_id": "GAP-002", "title": "Delayed diagnosis of HFpEF",
             "root_causes": {"primary_barrier_type": "competence", "contributing_factors": ["Symptom overlap", "Limited echo access"]}}
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Apply 2024 ACC/AHA guidelines for SGLT2 inhibitor initiation in HFpEF",
             "moore_classification": {"level": "Level 5", "category": "Performance"}, "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}},
            {"objective_id": "OBJ-002", "objective_text": "Identify comorbidities affecting HFpEF prognosis",
             "moore_classification": {"level": "Level 4", "category": "Competence"}}
        ]
    },
    "2_hyperthyroid": {
        "disease_state": "hyperthyroid disease",
        "therapeutic_area": "endocrinology",
        "target_audience": "endocrinologists",
        "estimated_reach": 400,
        "marketing_budget": 50000,
        "moore_level_target": "Level 5",
        "educational_format": "live symposium",
        "duration_minutes": 75,
        "modality": "virtual",
        "practice_settings": ["endocrine clinic", "primary care"],
        "project_title": "Excellence in Hyperthyroidism Management",
        "activity_title": "Thyroid CME Symposium 2026",
        "supporter_company": "ThyroMed Corp",
        "supporter_products": ["Tapazole", "Synthroid"],
        "competitor_products": ["PTU", "generic levothyroxine"],
        "gaps": [
            {"gap_id": "GAP-001", "title": "Delayed recognition of Graves disease",
             "root_causes": {"primary_barrier_type": "competence", "contributing_factors": ["Nonspecific symptoms", "Lack of screening"]}},
            {"gap_id": "GAP-002", "title": "Inconsistent treatment selection between ATDs and RAI",
             "root_causes": {"primary_barrier_type": "knowledge", "contributing_factors": ["Conflicting guidelines", "Patient preference"]}}
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Differentiate Graves disease from toxic nodular goiter",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
            {"objective_id": "OBJ-002", "objective_text": "Select appropriate initial therapy based on ATA guidelines",
             "moore_classification": {"level": "Level 5", "category": "Performance"}, "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}}
        ]
    },
    "3_chronic_cough": {
        "disease_state": "chronic cough",
        "therapeutic_area": "pulmonology",
        "target_audience": "pulmonologists",
        "estimated_reach": 600,
        "marketing_budget": 60000,
        "moore_level_target": "Level 5",
        "educational_format": "webinar",
        "duration_minutes": 75,
        "modality": "hybrid",
        "practice_settings": ["pulmonary clinic", "primary care"],
        "project_title": "Breaking the Chronic Cough Cycle",
        "activity_title": "Chronic Cough CME Webinar",
        "supporter_company": "CoughPharm LLC",
        "supporter_products": ["Gefapixant"],
        "competitor_products": ["Codeine", "Dextromethorphan"],
        "gaps": [
            {"gap_id": "GAP-001", "title": "Failure to identify refractory chronic cough",
             "root_causes": {"primary_barrier_type": "competence", "contributing_factors": ["Multiple etiologies", "Algorithm complexity"]}},
            {"gap_id": "GAP-002", "title": "Limited awareness of neuromodulatory therapies",
             "root_causes": {"primary_barrier_type": "knowledge", "contributing_factors": ["New drug approvals", "Limited experience"]}}
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Apply systematic diagnostic algorithm for unexplained chronic cough",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
            {"objective_id": "OBJ-002", "objective_text": "Prescribe appropriate neuromodulatory therapy for refractory chronic cough",
             "moore_classification": {"level": "Level 5", "category": "Performance"}, "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}}
        ]
    },
    "4_adhd": {
        "disease_state": "attention-deficit hyperactivity disorder",
        "therapeutic_area": "psychiatry",
        "target_audience": "psychiatrists",
        "estimated_reach": 700,
        "marketing_budget": 80000,
        "moore_level_target": "Level 5",
        "educational_format": "live symposium",
        "duration_minutes": 90,
        "modality": "hybrid",
        "practice_settings": ["psychiatry practice", "community mental health"],
        "project_title": "Adult ADHD: Bridging the Diagnosis Gap",
        "activity_title": "ADHD CME Symposium 2026",
        "supporter_company": "NeuroPharma Inc",
        "supporter_products": ["Vyvanse", "Adderall XR"],
        "competitor_products": ["Concerta", "Strattera", "Qelbree"],
        "gaps": [
            {"gap_id": "GAP-001", "title": "Underdiagnosis of adult ADHD",
             "root_causes": {"primary_barrier_type": "competence", "contributing_factors": ["Adult presentation differs", "Comorbidity overlap"]}},
            {"gap_id": "GAP-002", "title": "Stimulant prescribing hesitancy",
             "root_causes": {"primary_barrier_type": "attitude", "contributing_factors": ["Abuse concerns", "Regulatory pressure"]}},
            {"gap_id": "GAP-003", "title": "Racial and gender disparities in ADHD diagnosis",
             "root_causes": {"primary_barrier_type": "awareness", "contributing_factors": ["Implicit bias", "Limited diverse research"]}}
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Apply DSM-5-TR criteria for adult ADHD diagnosis across diverse populations",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
            {"objective_id": "OBJ-002", "objective_text": "Develop individualized treatment plans addressing patient preferences and comorbidities",
             "moore_classification": {"level": "Level 5", "category": "Performance"}, "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}}
        ]
    },
    "5_polymyalgia_rheumatica": {
        "disease_state": "polymyalgia rheumatica",
        "therapeutic_area": "rheumatology",
        "target_audience": "rheumatologists",
        "estimated_reach": 350,
        "marketing_budget": 45000,
        "moore_level_target": "Level 5",
        "educational_format": "webinar",
        "duration_minutes": 60,
        "modality": "virtual",
        "practice_settings": ["rheumatology clinic", "primary care"],
        "project_title": "PMR Management: Beyond Glucocorticoids",
        "activity_title": "PMR CME Webinar 2026",
        "supporter_company": "RheumaPharm LLC",
        "supporter_products": ["Actemra"],
        "competitor_products": ["Prednisone", "Methotrexate"],
        "gaps": [
            {"gap_id": "GAP-001", "title": "Delayed PMR diagnosis due to mimics",
             "root_causes": {"primary_barrier_type": "competence", "contributing_factors": ["Symptom overlap with RA and GCA", "Lack of biomarkers"]}},
            {"gap_id": "GAP-002", "title": "Inconsistent steroid tapering protocols",
             "root_causes": {"primary_barrier_type": "knowledge", "contributing_factors": ["Variable guidelines", "Patient-specific factors"]}},
            {"gap_id": "GAP-003", "title": "Limited awareness of tocilizumab for steroid-sparing",
             "root_causes": {"primary_barrier_type": "knowledge", "contributing_factors": ["Recent approval", "Limited experience"]}}
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Differentiate PMR from giant cell arteritis and rheumatoid arthritis",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
            {"objective_id": "OBJ-002", "objective_text": "Implement evidence-based steroid tapering protocols for PMR",
             "moore_classification": {"level": "Level 5", "category": "Performance"}, "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}},
            {"objective_id": "OBJ-003", "objective_text": "Identify appropriate candidates for tocilizumab steroid-sparing therapy",
             "moore_classification": {"level": "Level 5", "category": "Performance"}}
        ]
    }
}

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Setup logging to file and console."""
    log_dir = OUTPUT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"batch_run_{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    return log_file


# =============================================================================
# INPUT BUILDERS
# =============================================================================

def build_input(topic: Dict, agent: str) -> Dict[str, Any]:
    """Build agent-specific input from topic data."""
    
    base = {
        "target_audience": topic["target_audience"],
        "therapeutic_area": topic["therapeutic_area"],
        "disease_state": topic["disease_state"],
    }
    
    if agent == "learning_objectives":
        return {
            **base,
            "gap_analysis_report": {"gaps": topic["gaps"]},
            "moore_level_target": topic["moore_level_target"],
            "educational_format": topic["educational_format"],
            "outcome_goals": ["Improve guideline adherence", "Increase evidence-based practice"],
        }
    
    elif agent == "curriculum_design":
        return {
            **base,
            "learning_objectives_report": {"objectives": topic["objectives"]},
            "gap_analysis_report": {"gaps": topic["gaps"]},
            "duration_minutes": topic["duration_minutes"],
            "modality": topic["modality"],
            "practice_settings": topic["practice_settings"],
        }
    
    elif agent == "research_protocol":
        return {
            **base,
            "estimated_reach": topic["estimated_reach"],
            "moore_level_target": topic["moore_level_target"],
            "learning_objectives_report": {"objectives": topic["objectives"]},
            "gap_analysis_report": {"gaps": topic["gaps"]},
            "outcome_goals": ["Increase evidence-based practice", "Improve patient outcomes"],
        }
    
    elif agent == "marketing_plan":
        return {
            **base,
            "estimated_reach": topic["estimated_reach"],
            "marketing_budget": topic["marketing_budget"],
            "geographic_focus": "United States",
            "marketing_channels": ["email", "conferences", "journals"],
            "educational_format": topic["educational_format"],
            "practice_settings": topic["practice_settings"],
        }
    
    elif agent == "grant_writer":
        return {
            **base,
            "project_title": topic["project_title"],
            "activity_title": topic["activity_title"],
            "supporter_company": topic["supporter_company"],
            "supporter_contact": "Dr. Grant Contact",
            "requested_amount": f"${topic['marketing_budget'] + 100000:,}",
            "budget_breakdown": {"faculty": 50000, "technology": 25000, "marketing": topic["marketing_budget"], "outcomes": 30000, "admin": 20000},
            "needs_assessment_output": {},
            "learning_objectives_output": {},
            "curriculum_design_output": {},
            "research_protocol_output": {},
            "marketing_plan_output": {},
            "gap_analysis_output": {},
        }
    
    elif agent == "compliance_review":
        return {
            "grant_package": {
                "cover_letter": f"Dear {topic['supporter_company']}, We submit this grant for {topic['disease_state']} CME.",
                "executive_summary": f"This CME initiative addresses critical gaps in {topic['disease_state']} management",
                "needs_assessment": f"{topic['disease_state']} management has significant practice gaps",
            },
            "supporter_company": topic["supporter_company"],
            "supporter_products": topic["supporter_products"],
            "competitor_products": topic["competitor_products"],
            "accreditation_types": ["ACCME"],
        }
    
    return base


# =============================================================================
# API CLIENT
# =============================================================================

async def run_agent(agent_name: str, input_data: dict) -> Dict[str, Any]:
    """Run agent via LangGraph Cloud API."""
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=300) as client:
        # Create thread
        response = await client.post(f"{LANGGRAPH_URL}/threads", headers=headers, json={})
        thread = response.json()
        thread_id = thread["thread_id"]
        
        # Start run
        response = await client.post(
            f"{LANGGRAPH_URL}/threads/{thread_id}/runs",
            headers=headers,
            json={"assistant_id": agent_name, "input": input_data}
        )
        run = response.json()
        run_id = run["run_id"]
        
        # Wait for completion
        max_wait = 300  # 5 minutes max for complex agents
        waited = 0
        while waited < max_wait:
            response = await client.get(
                f"{LANGGRAPH_URL}/threads/{thread_id}/runs/{run_id}",
                headers=headers
            )
            run_status = response.json()
            status = run_status.get("status")
            
            if status == "success":
                break
            elif status in ["error", "failed"]:
                raise Exception(f"Run failed: {run_status.get('error', 'Unknown error')}")
            
            await asyncio.sleep(3)
            waited += 3
        
        if waited >= max_wait:
            raise Exception("Timeout waiting for agent completion")
        
        # Get final state
        response = await client.get(f"{LANGGRAPH_URL}/threads/{thread_id}/state", headers=headers)
        state = response.json()
        
        return state.get("values", {})


# =============================================================================
# MAIN BATCH RUNNER
# =============================================================================

async def run_batch():
    """Run all agents for all topics."""
    
    log_file = setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("CME AGENT BATCH RUN STARTED")
    logger.info(f"Topics: {len(TOPICS)} | Agents: {len(AGENTS)} | Total runs: {len(TOPICS) * len(AGENTS)}")
    logger.info("=" * 60)
    
    results = {
        "success": [],
        "failed": [],
        "total_tokens": 0,
        "total_cost": 0.0,
    }
    
    start_time = datetime.now()
    
    for topic_key, topic_data in TOPICS.items():
        topic_dir = OUTPUT_DIR / topic_key
        topic_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("-" * 40)
        logger.info(f"TOPIC: {topic_key} ({topic_data['disease_state']})")
        logger.info("-" * 40)
        
        for agent in AGENTS:
            run_key = f"{topic_key}/{agent}"
            logger.info(f"  Running: {agent}...")
            
            try:
                input_data = build_input(topic_data, agent)
                result = await run_agent(agent, input_data)
                
                # Extract document
                doc_field = DOCUMENT_FIELDS.get(agent)
                document = result.get(doc_field, "")
                
                # Handle dict output (e.g., compliance_review returns a dict)
                if isinstance(document, dict):
                    document = f"# {agent.replace('_', ' ').title()} Report\n\n```json\n{json.dumps(document, indent=2, default=str)}\n```"
                elif not document:
                    # Fallback: save full result as JSON
                    document = f"# {agent} Output\n\n```json\n{json.dumps(result, indent=2, default=str)}\n```"
                
                # Save file
                filepath = topic_dir / f"{agent}.md"
                with open(filepath, "w") as f:
                    f.write(document)
                
                # Track metrics
                tokens = result.get("total_tokens", 0)
                cost = result.get("total_cost", 0.0)
                results["total_tokens"] += tokens
                results["total_cost"] += cost
                results["success"].append(run_key)
                
                logger.info(f"  ✅ {agent}: {tokens:,} tokens, ${cost:.4f}")
                
            except Exception as e:
                error_msg = str(e)[:200]
                results["failed"].append({"run": run_key, "error": error_msg})
                logger.error(f"  ❌ {agent}: {error_msg}")
                
                # Save error file
                error_file = topic_dir / f"{agent}_ERROR.md"
                with open(error_file, "w") as f:
                    f.write(f"# Error: {agent}\n\n**Error:** {error_msg}\n\n**Input:**\n```json\n{json.dumps(input_data, indent=2)}\n```")
    
    # Summary
    elapsed = (datetime.now() - start_time).total_seconds()
    
    logger.info("=" * 60)
    logger.info("BATCH RUN COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Success: {len(results['success'])}/{len(TOPICS) * len(AGENTS)}")
    logger.info(f"Failed:  {len(results['failed'])}")
    logger.info(f"Tokens:  {results['total_tokens']:,}")
    logger.info(f"Cost:    ${results['total_cost']:.4f}")
    logger.info(f"Time:    {elapsed:.0f} seconds ({elapsed/60:.1f} minutes)")
    logger.info(f"Log:     {log_file}")
    
    if results["failed"]:
        logger.info("\nFailed runs:")
        for f in results["failed"]:
            logger.info(f"  - {f['run']}: {f['error']}")
    
    # Save summary
    summary_file = OUTPUT_DIR / "batch_summary.json"
    with open(summary_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": elapsed,
            **results
        }, f, indent=2)
    
    logger.info(f"Summary: {summary_file}")


if __name__ == "__main__":
    asyncio.run(run_batch())
