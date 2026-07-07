"""Prompts for intake_prefill_agent (extracted byte-identical, item 21)."""

PREFILL_SYSTEM_PROMPT = """You are a CME (Continuing Medical Education) intake form assistant.
Based on project information and a literature review, generate draft values for sections B through H of a CME intake form.
Return ONLY a JSON object — no markdown fences, no additional text."""

PREFILL_USER_TEMPLATE = """PROJECT INFORMATION:
- Project Name: {project_name}
- Therapeutic Area: {therapeutic_area}
- Disease State: {disease_state}
- Target Audience: {target_audience}
- HCP Types: {hcp_types}
{additional_context_block}
{research_context}

Generate a JSON object with this structure. Use the literature review to ground suggestions in evidence. For fields you cannot confidently suggest, use null.

{{
  "section_b": {{
    "supporter_name": "",
    "supporter_contact_name": null,
    "supporter_contact_email": null,
    "grant_amount_requested": <typical grant amount as number or null>,
    "grant_submission_deadline": null
  }},
  "section_c": {{
    "learning_format": "<webinar|live-symposium|enduring-module|workshop>",
    "duration_minutes": <integer>,
    "include_post_test": <true|false>,
    "include_pre_test": <true|false>,
    "faculty_count": <integer>
  }},
  "section_d": {{
    "clinical_topics": ["<topic>", ...],
    "treatment_modalities": ["<modality>", ...],
    "patient_population": "<description>",
    "stage_of_disease": "<description or null>",
    "comorbidities": ["<comorbidity>", ...]
  }},
  "section_e": {{
    "knowledge_gaps": ["<gap>", ...],
    "competence_gaps": ["<gap>", ...],
    "performance_gaps": ["<gap>", ...],
    "gap_evidence_sources": ["<source>", ...],
    "gap_priority": "<high|medium|low>"
  }},
  "section_f": {{
    "primary_outcomes": ["<outcome>", ...],
    "secondary_outcomes": ["<outcome>", ...],
    "measurement_approach": "<description>",
    "moore_levels_target": [<integers from 1-7>],
    "follow_up_timeline": "<timeline>"
  }},
  "section_g": {{
    "key_messages": ["<message>", ...],
    "required_references": ["PMID:<id> - <brief description>", ...],
    "excluded_topics": null,
    "competitor_products_to_mention": null,
    "regulatory_considerations": "<notes or null>"
  }},
  "section_h": {{
    "distribution_channels": ["<channel>", ...],
    "geo_restrictions": null,
    "language_requirements": ["English"],
    "target_launch_date": null,
    "expiration_date": null
  }},
  "confidence": {{
    "section_b": "low",
    "section_c": "<high|medium|low>",
    "section_d": "<high|medium|low>",
    "section_e": "<high|medium|low>",
    "section_f": "<high|medium|low>",
    "section_g": "<high|medium|low>",
    "section_h": "<high|medium|low>"
  }}
}}"""
