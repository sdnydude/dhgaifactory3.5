import os
#!/usr/bin/env python3
"""
Re-run only the failed agents from the batch run.
"""

import json
import httpx
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# =============================================================================
# CONFIGURATION
# =============================================================================

LANGGRAPH_URL = "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app"
API_KEY = os.environ.get("LANGGRAPH_API_KEY", "")
OUTPUT_DIR = Path("/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/outputs")

# Failed runs to retry
FAILED_RUNS = [
    ("1_hfpef", "compliance_review"),
    ("2_hyperthyroid", "curriculum_design"),
    ("2_hyperthyroid", "compliance_review"),
    ("3_chronic_cough", "compliance_review"),
    ("4_adhd", "compliance_review"),
    ("5_polymyalgia_rheumatica", "curriculum_design"),
    ("5_polymyalgia_rheumatica", "marketing_plan"),
    ("5_polymyalgia_rheumatica", "compliance_review"),
]

DOCUMENT_FIELDS = {
    "learning_objectives": "learning_objectives_document",
    "curriculum_design": "curriculum_document",
    "research_protocol": "protocol_document",
    "marketing_plan": "marketing_document",
    "grant_writer": "grant_document",
    "compliance_review": "compliance_report",
}

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
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Apply 2024 ACC/AHA guidelines for SGLT2 inhibitor initiation in HFpEF",
             "moore_classification": {"level": "Level 5", "category": "Performance"}, "measurement": {"primary_method": "Commitment-to-change", "timing": "60 days"}},
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
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Differentiate Graves disease from toxic nodular goiter",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
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
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Apply systematic diagnostic algorithm for unexplained chronic cough",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
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
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Apply DSM-5-TR criteria for adult ADHD diagnosis across diverse populations",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
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
        ],
        "objectives": [
            {"objective_id": "OBJ-001", "objective_text": "Differentiate PMR from giant cell arteritis and rheumatoid arthritis",
             "moore_classification": {"level": "Level 4", "category": "Competence"}},
        ]
    }
}

def build_input(topic: Dict, agent: str) -> Dict[str, Any]:
    """Build agent-specific input from topic data."""
    
    base = {
        "target_audience": topic["target_audience"],
        "therapeutic_area": topic["therapeutic_area"],
        "disease_state": topic["disease_state"],
    }
    
    if agent == "curriculum_design":
        return {
            **base,
            "learning_objectives_report": {"objectives": topic["objectives"]},
            "gap_analysis_report": {"gaps": topic["gaps"]},
            "duration_minutes": topic["duration_minutes"],
            "modality": topic["modality"],
            "practice_settings": topic["practice_settings"],
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


async def run_agent(agent_name: str, input_data: dict) -> Dict[str, Any]:
    """Run agent via LangGraph Cloud API."""
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=360) as client:
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
        
        # Wait for completion - 5 minute timeout
        max_wait = 300
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


async def run_retry():
    """Re-run failed agents."""
    
    logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 60)
    logger.info("RE-RUNNING FAILED AGENTS")
    logger.info(f"Failed runs to retry: {len(FAILED_RUNS)}")
    logger.info("=" * 60)
    
    success_count = 0
    failed_count = 0
    
    for topic_key, agent in FAILED_RUNS:
        topic_data = TOPICS[topic_key]
        topic_dir = OUTPUT_DIR / topic_key
        topic_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Running: {topic_key}/{agent}...")
        
        try:
            input_data = build_input(topic_data, agent)
            result = await run_agent(agent, input_data)
            
            # Extract document
            doc_field = DOCUMENT_FIELDS.get(agent)
            document = result.get(doc_field, "")
            
            # Handle dict output
            if isinstance(document, dict):
                document = f"# {agent.replace('_', ' ').title()} Report\n\n```json\n{json.dumps(document, indent=2, default=str)}\n```"
            elif not document:
                document = f"# {agent} Output\n\n```json\n{json.dumps(result, indent=2, default=str)}\n```"
            
            # Save file
            filepath = topic_dir / f"{agent}.md"
            with open(filepath, "w") as f:
                f.write(document)
            
            tokens = result.get("total_tokens", 0)
            cost = result.get("total_cost", 0.0)
            
            logger.info(f"✅ {topic_key}/{agent}: {tokens:,} tokens, ${cost:.4f}")
            success_count += 1
            
            # Remove error file if exists
            error_file = topic_dir / f"{agent}_ERROR.md"
            if error_file.exists():
                error_file.unlink()
            
        except Exception as e:
            error_msg = str(e)[:200]
            logger.error(f"❌ {topic_key}/{agent}: {error_msg}")
            failed_count += 1
    
    logger.info("=" * 60)
    logger.info(f"RETRY COMPLETE: {success_count} success, {failed_count} failed")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_retry())
