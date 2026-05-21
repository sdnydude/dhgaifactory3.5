"""CME sync service — LangGraph Cloud thread sync, extractors, and embedding generation."""
from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from models import (
    CMEAgentOutput, CMEDocument, CMEIntakeField, CMEProject, CMESourceReference,
)

logger = logging.getLogger(__name__)


THREAD_STATUS_MAP = {
    "busy": "processing",
    "interrupted": "review",
    "error": "failed",
}

NODE_TO_AGENT = {
    "initialize": "initializing",
    "early_research": "research",
    "gap_analysis": "gap_analysis",
    "learning_objectives": "learning_objectives",
    "needs_assessment": "needs_assessment",
    "prose_quality": "prose_quality",
    "prose_quality_1": "prose_quality_1",
    "design_phase": "design_phase",
    "grant_writer": "grant_writer",
    "prose_quality_2": "prose_quality_2",
    "compliance": "compliance",
    "human_review": "human_review",
    "human_review_pq1": "human_review",
    "human_review_pq2": "human_review",
    "auto_approve": "auto_approve",
    "process_feedback": "processing_feedback",
    "complete": "complete",
    "failed": "failed",
}

AGENT_OUTPUT_META = {
    "research_output": ("research", "Research & Literature Review"),
    "clinical_output": ("clinical", "Clinical Practice Analysis"),
    "gap_analysis_output": ("gap_analysis", "Gap Analysis"),
    "needs_assessment_output": ("needs_assessment", "Needs Assessment"),
    "learning_objectives_output": ("learning_objectives", "Learning Objectives"),
    "curriculum_output": ("curriculum", "Curriculum Design"),
    "protocol_output": ("protocol", "Research Protocol"),
    "marketing_output": ("marketing", "Marketing Plan"),
    "grant_package_output": ("grant_package", "Grant Package"),
    "prose_quality_pass_1": ("prose_quality_1", "Prose Quality Pass 1"),
    "prose_quality_pass_2": ("prose_quality_2", "Prose Quality Pass 2"),
    "compliance_result": ("compliance", "Compliance Review"),
}

DOCUMENT_TEXT_PATHS = {
    "research": "research_document",
    "clinical": "clinical_practice_document",
    "gap_analysis": "gap_analysis_document",
    "needs_assessment": "complete_document",
    "learning_objectives": "learning_objectives_document",
    "curriculum": "curriculum_document",
    "protocol": "protocol_document",
    "marketing": "marketing_document",
    "grant_package": "complete_document_markdown",
    "prose_quality_1": "summary",
    "prose_quality_2": "summary",
    "compliance": None,
}

REPORT_PATHS = {
    "research": "research_report",
    "clinical": "clinical_practice_report",
    "gap_analysis": "gap_analysis_report",
    "learning_objectives": "learning_objectives_report",
    "curriculum": "curriculum_report",
    "protocol": "protocol_report",
    "marketing": "marketing_report",
    "compliance": "compliance_report",
}

CITATION_PATHS = {
    "research": ("research_report", "citations"),
    "clinical": ("clinical_practice_report", "citations"),
}

FIELD_LABELS = {
    "section_a": {
        "project_name": "Project Name",
        "therapeutic_area": "Therapeutic Area",
        "disease_state": "Disease State",
        "target_audience_primary": "Primary Target Audience",
        "target_audience_secondary": "Secondary Target Audience",
        "target_hcp_types": "Target HCP Types",
    },
    "section_b": {
        "supporter_name": "Supporter Name",
        "supporter_contact_name": "Supporter Contact Name",
        "supporter_contact_email": "Supporter Contact Email",
        "grant_amount_requested": "Grant Amount Requested",
        "grant_submission_deadline": "Grant Submission Deadline",
    },
    "section_c": {
        "learning_format": "Learning Format",
        "duration_minutes": "Duration (minutes)",
        "faculty_count": "Faculty Count",
        "include_pre_test": "Include Pre-Test",
        "include_post_test": "Include Post-Test",
    },
    "section_d": {
        "clinical_topics": "Clinical Topics",
        "treatment_modalities": "Treatment Modalities",
        "patient_population": "Patient Population",
        "stage_of_disease": "Stage of Disease",
        "comorbidities": "Comorbidities",
    },
    "section_e": {
        "knowledge_gaps": "Knowledge Gaps",
        "competence_gaps": "Competence Gaps",
        "performance_gaps": "Performance Gaps",
        "gap_evidence_sources": "Gap Evidence Sources",
        "gap_priority": "Gap Priority",
    },
    "section_f": {
        "primary_outcomes": "Primary Outcomes",
        "secondary_outcomes": "Secondary Outcomes",
        "measurement_approach": "Measurement Approach",
        "moore_levels_target": "Moore Levels Target",
        "follow_up_timeline": "Follow-Up Timeline",
    },
    "section_g": {
        "key_messages": "Key Messages",
        "required_references": "Required References",
        "excluded_topics": "Excluded Topics",
        "competitor_products_to_mention": "Competitor Products",
        "regulatory_considerations": "Regulatory Considerations",
    },
    "section_h": {
        "target_launch_date": "Target Launch Date",
        "expiration_date": "Expiration Date",
        "distribution_channels": "Distribution Channels",
        "geo_restrictions": "Geographic Restrictions",
        "language_requirements": "Language Requirements",
    },
    "section_i": {
        "accme_compliant": "ACCME Compliant",
        "financial_disclosure_required": "Financial Disclosure Required",
        "off_label_discussion": "Off-Label Discussion",
        "commercial_support_acknowledgment": "Commercial Support Acknowledgment",
    },
    "section_j": {
        "special_instructions": "Special Instructions",
        "reference_materials": "Reference Materials",
        "internal_notes": "Internal Notes",
    },
}


def extract_document_text(agent_name: str, content: Dict[str, Any]) -> Optional[str]:
    if not isinstance(content, dict):
        return None

    text_path = DOCUMENT_TEXT_PATHS.get(agent_name)
    if text_path is None and agent_name == "compliance":
        report = content.get("compliance_report", {})
        if isinstance(report, dict):
            verdict = report.get("overall_verdict", "")
            checks = report.get("standard_checks", {})
            parts = [f"Compliance Verdict: {verdict}"]
            for std_name, std_data in checks.items():
                if isinstance(std_data, dict):
                    parts.append(f"{std_name}: {std_data.get('status', 'unknown')} — {std_data.get('findings', '')}")
            return "\n\n".join(parts) if parts else None
        return None

    if text_path:
        text_val = content.get(text_path)
        if isinstance(text_val, str) and len(text_val) > 10:
            return text_val
    return None


def extract_quality_score(agent_name: str, content: Dict[str, Any]) -> Optional[float]:
    if not isinstance(content, dict):
        return None

    if agent_name in ("prose_quality_1", "prose_quality_2"):
        score = content.get("overall_score")
        if isinstance(score, (int, float)):
            return score / 100.0
    elif agent_name == "needs_assessment":
        if content.get("quality_passed"):
            return 1.0
        word_count = content.get("word_count", 0)
        if isinstance(word_count, (int, float)) and word_count > 0:
            return min(word_count / 3100.0, 1.0)
    elif agent_name == "compliance":
        report = content.get("compliance_report", {})
        if isinstance(report, dict):
            verdict = report.get("overall_verdict", "")
            if verdict == "APPROVED":
                return 1.0
            elif verdict == "REQUIRES_REVISION":
                return 0.5
            elif verdict == "REJECTED":
                return 0.0
    return None


def extract_quality_details(agent_name: str, content: Dict[str, Any]) -> Optional[Dict]:
    if not isinstance(content, dict):
        return None

    if agent_name in ("prose_quality_1", "prose_quality_2"):
        return {
            "overall_score": content.get("overall_score"),
            "overall_passed": content.get("overall_passed"),
            "prose_density_score": content.get("prose_density_score"),
            "ai_patterns_count": content.get("ai_patterns_count"),
            "word_count_total": content.get("word_count_total"),
            "revision_instructions": content.get("revision_instructions"),
        }
    elif agent_name == "needs_assessment":
        return {
            "word_count": content.get("word_count"),
            "meets_word_count": content.get("meets_word_count"),
            "prose_density": content.get("prose_density"),
            "quality_passed": content.get("quality_passed"),
            "section_word_counts": content.get("section_word_counts"),
            "character_appearances": content.get("character_appearances"),
        }
    elif agent_name == "compliance":
        report = content.get("compliance_report", {})
        if isinstance(report, dict):
            return {
                "overall_verdict": report.get("overall_verdict"),
                "remediation_required": report.get("remediation_required"),
                "standard_checks": report.get("standard_checks"),
                "bias_issues": report.get("bias_issues"),
            }
    return None


def extract_word_count(agent_name: str, content: Dict[str, Any]) -> Optional[int]:
    if not isinstance(content, dict):
        return None

    if agent_name == "needs_assessment":
        wc = content.get("word_count")
        if isinstance(wc, int):
            return wc
    elif agent_name in ("prose_quality_1", "prose_quality_2"):
        wc = content.get("word_count_total")
        if isinstance(wc, int):
            return wc

    doc_text = extract_document_text(agent_name, content)
    if doc_text:
        return len(doc_text.split())
    return None


def extract_citations(agent_name: str, content: Dict[str, Any]) -> List[Dict[str, Any]]:
    if agent_name not in CITATION_PATHS or not isinstance(content, dict):
        return []

    report_key, citations_key = CITATION_PATHS[agent_name]
    report = content.get(report_key, {})
    if not isinstance(report, dict):
        return []

    citations = report.get(citations_key, [])
    if not isinstance(citations, list):
        return []

    return citations


def extract_intake_fields(project_id, intake_jsonb: Dict[str, Any], db: Session) -> int:
    if not isinstance(intake_jsonb, dict):
        return 0

    count = 0
    for section_key, section_data in intake_jsonb.items():
        if not isinstance(section_data, dict):
            continue
        labels = FIELD_LABELS.get(section_key, {})

        for field_name, value in section_data.items():
            label = labels.get(field_name, field_name.replace("_", " ").title())

            if isinstance(value, (list, dict)):
                value_text = str(value) if value else None
                value_json = value
            elif isinstance(value, bool):
                value_text = "Yes" if value else "No"
                value_json = None
            elif value is not None:
                value_text = str(value)
                value_json = None
            else:
                value_text = None
                value_json = None

            existing = db.query(CMEIntakeField).filter(
                CMEIntakeField.project_id == project_id,
                CMEIntakeField.section == section_key,
                CMEIntakeField.field_name == field_name,
            ).first()

            if existing:
                existing.value_text = value_text
                existing.value_json = value_json
                existing.field_label = label
            else:
                db.add(CMEIntakeField(
                    project_id=project_id,
                    section=section_key,
                    field_name=field_name,
                    field_label=label,
                    value_text=value_text,
                    value_json=value_json,
                ))
            count += 1

    return count


async def generate_embedding(text: str) -> Optional[List[float]]:
    if not text or len(text.strip()) < 10:
        return None

    truncated = text[:32000]

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{os.getenv('OLLAMA_URL', 'http://dhg-ollama:11434')}/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": truncated},
            )
            resp.raise_for_status()
            data = resp.json()
            embedding = data.get("embedding")
            if isinstance(embedding, list) and len(embedding) == 768:
                return embedding
    except Exception as e:
        logger.warning(f"Embedding generation failed: {e}")
    return None


def calculate_progress(agents_completed: list[str]) -> int:
    total_agents = len(AGENT_OUTPUT_META)
    return int((len(agents_completed) / total_agents) * 100)


async def sync_project_from_thread(
    project: CMEProject,
    thread_data: Dict[str, Any],
    db: Session,
) -> Dict[str, Any]:
    thread_info = thread_data["thread"]
    thread_state = thread_data["state"]
    values = thread_state.get("values") or {}
    thread_status = thread_info.get("status", "idle")

    if thread_status == "idle":
        pipeline_status = values.get("status", "complete")
        if pipeline_status in ("complete", "approved"):
            new_status = "complete"
        elif pipeline_status == "failed":
            new_status = "failed"
        else:
            new_status = project.status
    else:
        new_status = THREAD_STATUS_MAP.get(thread_status, project.status)

    old_status = project.status
    project.status = new_status

    next_nodes = thread_state.get("next") or []
    if next_nodes:
        active_node = next_nodes[0]
        project.current_agent = NODE_TO_AGENT.get(active_node, active_node)
    else:
        project.current_agent = values.get("current_step", project.current_agent)

    project.human_review_status = values.get("human_review_status", project.human_review_status)
    project.human_review_notes = values.get("human_review_notes", project.human_review_notes)

    agents_completed = []
    documents_created = 0
    references_created = 0

    for state_key, (agent_name, doc_title) in AGENT_OUTPUT_META.items():
        output = values.get(state_key)
        if not output or not isinstance(output, dict):
            continue

        agents_completed.append(agent_name)
        doc_text = extract_document_text(agent_name, output)
        quality_score = extract_quality_score(agent_name, output)

        existing_output = db.query(CMEAgentOutput).filter(
            CMEAgentOutput.project_id == project.id,
            CMEAgentOutput.agent_name == agent_name,
        ).first()

        if existing_output:
            if doc_text and not existing_output.document_text:
                existing_output.document_text = doc_text
            if quality_score is not None and existing_output.quality_score is None:
                existing_output.quality_score = quality_score
            agent_output_id = existing_output.id
        else:
            new_output = CMEAgentOutput(
                project_id=project.id,
                agent_name=agent_name,
                output_type="document",
                content=output,
                quality_score=quality_score,
                document_text=doc_text,
            )
            db.add(new_output)
            db.flush()
            agent_output_id = new_output.id

        if doc_text:
            existing_doc = db.query(CMEDocument).filter(
                CMEDocument.project_id == project.id,
                CMEDocument.document_type == agent_name,
                CMEDocument.is_current == True,
            ).first()

            if not existing_doc:
                now = datetime.utcnow()
                doc = CMEDocument(
                    project_id=project.id,
                    agent_output_id=agent_output_id,
                    document_type=agent_name,
                    version=1,
                    is_current=True,
                    title=doc_title,
                    content_text=doc_text,
                    content_json=output,
                    word_count=extract_word_count(agent_name, output),
                    quality_score=quality_score,
                    quality_passed=output.get("quality_passed") or output.get("overall_passed"),
                    quality_details=extract_quality_details(agent_name, output),
                    created_by="langgraph_pipeline",
                    retention_until=datetime(now.year + 7, now.month, now.day),
                )
                db.add(doc)
                documents_created += 1

        citations = extract_citations(agent_name, output)
        for cit in citations:
            if not isinstance(cit, dict):
                continue
            ref_id = str(cit.get("pmid", cit.get("doi", "")))
            if not ref_id:
                continue

            existing_ref = db.query(CMESourceReference).filter(
                CMESourceReference.project_id == project.id,
                CMESourceReference.ref_id == ref_id,
            ).first()

            if not existing_ref:
                db.add(CMESourceReference(
                    project_id=project.id,
                    ref_type="pubmed" if cit.get("pmid") else "doi",
                    ref_id=ref_id,
                    title=cit.get("title", "Untitled"),
                    authors=cit.get("authors", ""),
                    journal=cit.get("journal", ""),
                    url=cit.get("url", ""),
                    abstract=cit.get("abstract", ""),
                    cached_content=cit,
                ))
                references_created += 1

    if agents_completed:
        project.agents_completed = agents_completed
        remaining = [a for a in (project.agents_pending or []) if a not in agents_completed]
        project.agents_pending = remaining
        project.progress_percent = calculate_progress(agents_completed)

    if new_status == "complete" and not project.completed_at:
        project.completed_at = datetime.utcnow()

    cloud_errors = values.get("errors")
    if cloud_errors:
        project.errors = cloud_errors

    existing_intake_count = db.query(CMEIntakeField).filter(
        CMEIntakeField.project_id == project.id,
    ).count()
    intake_fields_created = 0
    if existing_intake_count == 0 and project.intake:
        intake_fields_created = extract_intake_fields(project.id, project.intake, db)

    db.commit()
    db.refresh(project)

    try:
        outputs_needing_embeddings = db.query(CMEAgentOutput).filter(
            CMEAgentOutput.project_id == project.id,
            CMEAgentOutput.document_text.isnot(None),
            CMEAgentOutput.embedding.is_(None),
        ).all()

        for ao in outputs_needing_embeddings:
            emb = await generate_embedding(ao.document_text)
            if emb:
                db.execute(
                    CMEAgentOutput.__table__.update()
                    .where(CMEAgentOutput.id == ao.id)
                    .values(embedding=emb)
                )

        docs_needing_embeddings = db.query(CMEDocument).filter(
            CMEDocument.project_id == project.id,
            CMEDocument.embedding.is_(None),
        ).all()

        for doc in docs_needing_embeddings:
            emb = await generate_embedding(doc.content_text)
            if emb:
                db.execute(
                    CMEDocument.__table__.update()
                    .where(CMEDocument.id == doc.id)
                    .values(embedding=emb)
                )

        refs_needing_embeddings = db.query(CMESourceReference).filter(
            CMESourceReference.project_id == project.id,
            CMESourceReference.embedding.is_(None),
            CMESourceReference.abstract.isnot(None),
        ).all()

        for ref in refs_needing_embeddings:
            ref_text = f"{ref.title} {ref.authors or ''} {ref.abstract or ''}"
            emb = await generate_embedding(ref_text)
            if emb:
                db.execute(
                    CMESourceReference.__table__.update()
                    .where(CMESourceReference.id == ref.id)
                    .values(embedding=emb)
                )

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Embedding generation failed for project {project.id}: {e}")

    return {
        "project_id": str(project.id),
        "old_status": old_status,
        "new_status": new_status,
        "thread_status": thread_status,
        "agents_completed": agents_completed,
        "documents_created": documents_created,
        "references_created": references_created,
        "intake_fields_created": intake_fields_created,
        "progress_percent": project.progress_percent,
    }
