"""
Shared topic extraction node for all CME agents.
=================================================
Parses free-text chat messages into the structured fields
(disease_state, therapeutic_area, target_audience, geographic_focus)
that all downstream agent nodes require.

When invoked via structured intake (disease_state already set), this is a no-op.
"""

import re
import json

from langsmith import traceable
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


THERAPEUTIC_AREAS = [
    "cardiology", "oncology", "neurology", "pulmonology", "gastroenterology",
    "endocrinology", "rheumatology", "infectious_disease", "dermatology",
    "psychiatry", "nephrology", "hematology", "immunology", "primary_care",
    "orthopedics", "urology", "ophthalmology", "pediatrics", "geriatrics",
    "emergency_medicine", "critical_care", "pain_management", "obesity_medicine",
]

_llm = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=1024)
COST_PER_1K_INPUT = 0.003
COST_PER_1K_OUTPUT = 0.015


@traceable(name="extract_topic_node", run_type="chain")
async def extract_topic_node(state: dict) -> dict:
    """Extract structured fields from the user's chat message.

    Compatible with any agent state that includes:
      - messages: list (chat messages from frontend)
      - disease_state: str (structured intake field)
      - therapeutic_area, target_audience, geographic_focus: str

    If disease_state is already populated, returns empty dict (no-op).
    """
    if state.get("disease_state"):
        return {}

    messages = state.get("messages", [])
    if not messages:
        return {"errors": (state.get("errors", []) or []) + ["No messages or disease_state provided"]}

    last_message = messages[-1]
    user_text = last_message.content if hasattr(last_message, "content") else str(last_message)

    system = f"""You are a medical education intake specialist. Extract structured fields from the user's request.

Return ONLY valid JSON with these fields:
{{
    "disease_state": "the specific disease or condition to research",
    "therapeutic_area": "one of: {', '.join(THERAPEUTIC_AREAS)}",
    "target_audience": "the intended clinician audience (default: 'physicians')",
    "geographic_focus": "geographic scope (default: 'United States')"
}}

Rules:
- disease_state must be the specific condition (e.g. "obesity", "heart failure", "type 2 diabetes")
- therapeutic_area must match the medical specialty that MANAGES this condition:
  - obesity → obesity_medicine or endocrinology (NOT rheumatology)
  - joint pain → orthopedics or rheumatology
  - diabetes → endocrinology
  - If user says "primary care", use primary_care
- If the user explicitly names a specialty or audience, use that for target_audience
- Extract only what is stated or clearly implied; use defaults otherwise"""

    prompt = f"Extract research parameters from this request:\n\n{user_text}"

    response = await _llm.ainvoke(
        [SystemMessage(content=system), HumanMessage(content=prompt)],
        config={"metadata": {"step": "extract_topic"}}
    )

    input_tokens = 0
    output_tokens = 0
    if hasattr(response, "usage_metadata") and response.usage_metadata:
        input_tokens = response.usage_metadata.get("input_tokens", 0)
        output_tokens = response.usage_metadata.get("output_tokens", 0)
    cost = (input_tokens / 1000 * COST_PER_1K_INPUT) + (output_tokens / 1000 * COST_PER_1K_OUTPUT)

    try:
        content = response.content
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            extracted = json.loads(json_match.group())
        else:
            return {"errors": (state.get("errors", []) or []) + [f"Failed to parse topic from: {user_text[:100]}"]}
    except json.JSONDecodeError:
        return {"errors": (state.get("errors", []) or []) + [f"Invalid JSON in topic extraction for: {user_text[:100]}"]}

    prev_tokens = state.get("total_tokens", 0) or 0
    prev_cost = state.get("total_cost", 0.0) or 0.0

    return {
        "disease_state": extracted.get("disease_state", ""),
        "therapeutic_area": extracted.get("therapeutic_area", "primary_care"),
        "target_audience": extracted.get("target_audience", "physicians"),
        "geographic_focus": extracted.get("geographic_focus", "United States"),
        "total_tokens": prev_tokens + input_tokens + output_tokens,
        "total_cost": prev_cost + cost,
        "messages": [HumanMessage(content=f"Topic extracted: {extracted.get('disease_state', 'unknown')} ({extracted.get('therapeutic_area', 'unknown')})")],
    }
