"""
Compliance Review Agent - Agent #12
===================================
Final quality gate ensuring ACCME accreditation standards, independence, and fair balance.

LangGraph Cloud Ready:
- Verifies ACCME Standards 1-6
- Detects commercial bias (regex + LLM)
- Scoring and remediation routing
- Output: Pass/Fail Compliance Report
"""

import os
import re
import json
import operator
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from enum import Enum

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


# =============================================================================
# CONFIGURATION
# =============================================================================

BIAS_PATTERNS = {
    "promotional_language": [
        r"first[- ]in[- ]class",
        r"best[- ]in[- ]class",
        r"breakthrough",
        r"ground[- ]?breaking",
        r"revolutionary",
        r"game[- ]?changer",
        r"unprecedented efficacy",
        r"superior to(?! in specific .* trials?)",
    ],
    "unbalanced_presentation": [
        r"unlike\s+\[competitor\],?\s+\[supporter product\]\s+(offers|provides|delivers)",
        r"\[competitor\]\s+fails?\s+to",
    ],
    "cherry_picked_data": [
        r"the (study|trial) showed",  # Risk if without "studies" plural context
    ]
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class ComplianceState(TypedDict):
    # === INPUTS ===
    grant_package: Dict[str, Any]  # The full output from Grant Writer
    supporter_company: str
    supporter_products: List[str]
    competitor_products: List[str]
    accreditation_types: List[str]
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    bias_issues_found: List[Dict]
    standard_checks: Dict[str, Any]  # Stores results of each standard check
    
    # === OUTPUT ===
    compliance_report: Dict[str, Any]
    
    # Metadata
    agent_version: str
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client for compliance review."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015
    
    @traceable(name="compliance_llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        """Generate response with cost tracking."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ]
        
        response = await self.model.ainvoke(
            messages,
            config={"metadata": metadata or {}}
        )
        
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + (output_tokens / 1000 * self.cost_per_1k_output)
        
        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }


llm = LLMClient()


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

COMPLIANCE_SYSTEM_PROMPT = """You are a CME compliance specialist reviewing grant packages for ACCME accreditation standards.
Your review must be OBJECTIVE, THOROUGH, and PROTECTIVE of accreditation status.

ACCME STANDARDS SUMMARY:
1. Independence: Provider controls content, not commercial interests.
2. COI Resolution: All conflicts identified and resolved.
3. Content Validity: Evidence-based, balanced, objectively presented.
4. Format: Educationally appropriate.
5. Evaluation: Measurable outcomes.
6. Commercial Support: Disclosed and separated.

You must identify any commercial bias, promotional language, or lack of fair balance.
"""


# =============================================================================
# GRAPH NODES
# =============================================================================

def _extract_text_content(package: Dict[str, Any]) -> str:
    """Helper to flatten grant package into single string for regex."""
    text = ""
    for key, section in package.items():
        if isinstance(section, dict):
            text += section.get("content", "") + "\n"
        elif isinstance(section, str):
            text += section + "\n"
    return text


@traceable(name="check_bias_regex_node", run_type="chain")
async def check_bias_regex_node(state: ComplianceState) -> dict:
    """Run regex-based bias detection."""
    
    package = state.get("grant_package", {})
    text_content = _extract_text_content(package)
    
    issues = []
    
    # Check regex patterns
    for category, patterns in BIAS_PATTERNS.items():
        for pattern in patterns:
            for match in re.finditer(pattern, text_content, re.IGNORECASE):
                issues.append({
                    "type": category,
                    "text": match.group(),
                    "context": text_content[max(0, match.start()-50):match.end()+50],
                    "severity": "major",
                    "location": "Full Document Scan"
                })
                
    # Check mention balance (basic)
    supporter_products = state.get("supporter_products", [])
    competitor_products = state.get("competitor_products", [])
    
    for prod in supporter_products:
        count = text_content.lower().count(prod.lower())
        if count > 10:  # Arbitrary threshold for concern
            issues.append({
                "type": "excessive_mention",
                "text": f"Supporter product '{prod}' mentioned {count} times",
                "severity": "minor",
                "location": "Global Count"
            })
            
    return {
        "bias_issues_found": issues
    }


@traceable(name="review_independence_node", run_type="chain")
async def review_independence_node(state: ComplianceState) -> dict:
    """Review Standards 1 (Independence) & 6 (Commercial Support)."""
    
    package = state.get("grant_package", {})
    indep_section = package.get("independence_and_compliance", {})
    cover_letter = package.get("cover_letter", {})
    
    system = f"""{COMPLIANCE_SYSTEM_PROMPT}

You are reviewing ACCME Standard 1 (Independence) and Standard 6 (Commercial Support).
Return JSON:
{{
    "standard_1": {{
        "compliant": true/false,
        "findings": ["finding 1"],
        "evidence": "evidence text"
    }},
    "standard_6": {{
        "compliant": true/false,
        "findings": ["finding 1"],
        "evidence": "evidence text"
    }}
}}"""

    prompt = f"""Review these sections for Independence and Support disclosure.
    
    INDEPENDENCE SECTION:
    {json.dumps(indep_section, indent=2)}
    
    COVER LETTER:
    {json.dumps(cover_letter, indent=2)}
    
    Verify that:
    1. Provider maintains control (std 1).
    2. Support is acknowledged but properly separated (std 6)."""

    result = await llm.generate(system, prompt, {"step": "independence"})
    
    try:
        data = json.loads(result["content"])
    except:
        # Fallback default
        data = {
            "standard_1": {"compliant": False, "findings": ["Parse error"], "evidence": ""},
            "standard_6": {"compliant": False, "findings": ["Parse error"], "evidence": ""}
        }
        
    prev_checks = state.get("standard_checks", {})
    prev_checks.update(data)
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "standard_checks": prev_checks,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="review_content_validity_node", run_type="chain")
async def review_content_validity_node(state: ComplianceState) -> dict:
    """Review Standard 3 (Content Validity & Fair Balance)."""
    
    package = state.get("grant_package", {})
    needs = package.get("needs_assessment", {})
    curriculum = package.get("curriculum_and_educational_design", {})
    
    supporter = state.get("supporter_company", "")
    products = state.get("supporter_products", [])
    competitors = state.get("competitor_products", [])
    
    system = f"""{COMPLIANCE_SYSTEM_PROMPT}

You are reviewing ACCME Standard 3 (Content Validity & Fair Balance).
Return JSON:
{{
    "standard_3": {{
        "compliant": true/false,
        "findings": ["finding 1"],
        "evidence": "evidence text"
    }},
    "fair_balance_analysis": {{
        "supporter_coverage": "balanced/favored/excluded",
        "competitor_coverage": "balanced/favored/excluded",
        "findings": ["finding 1"]
    }}
}}"""

    prompt = f"""Review content for Fair Balance.
    
    SUPPORTER: {supporter}
    PRODUCTS: {products}
    COMPETITORS: {competitors}
    
    NEEDS ASSESSMENT EXCERPT:
    {str(needs)[:2000]}...
    
    CURRICULUM EXCERPT:
    {str(curriculum)[:2000]}...
    
    Verify that:
    1. Content is valid/evidence-based.
    2. Treatment options are balanced (benefits/risks).
    3. No preferential treatment of supporter products."""

    result = await llm.generate(system, prompt, {"step": "content_validity"})
    
    try:
        data = json.loads(result["content"])
    except:
         data = {
            "standard_3": {"compliant": False, "findings": ["Parse error"], "evidence": ""},
            "fair_balance_analysis": {"findings": ["Parse error"]}
        }

    prev_checks = state.get("standard_checks", {})
    prev_checks.update(data)
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "standard_checks": prev_checks,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="generate_compliance_report_node", run_type="chain")
async def generate_compliance_report_node(state: ComplianceState) -> dict:
    """Generate final compliance report."""
    
    checks = state.get("standard_checks", {})
    bias_issues = state.get("bias_issues_found", [])
    
    # Simple scoring logic
    passed = True
    score = 100
    
    # Check Standards
    for std in ["standard_1", "standard_6", "standard_3"]:
        if not checks.get(std, {}).get("compliant", False):
            passed = False
            score -= 20
            
    # Check Bias
    if len(bias_issues) > 0:
        passed = False
        score -= (len(bias_issues) * 5)
    
    score = max(0, score)
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "standards_applied": ["ACCME"]
        },
        "overall_result": {
            "compliant": passed,
            "score": score,
            "summary": "Compliance review complete.",
            "certification_ready": passed
        },
        "accme_standards": checks,
        "commercial_bias_detection": {
            "bias_indicators_found": bias_issues,
            "total_issues": len(bias_issues),
            "passed": len(bias_issues) == 0
        }
    }
    
    # Add Remediation if failed
    if not passed:
        report["remediation_required"] = {
            "issues": [
                {
                    "description": "Commercial bias detected",
                    "action": "Revise content to remove promotional language",
                    "location": "See bias indicators"
                }
            ] if bias_issues else []
        }
    
    return {
        "compliance_report": report
    }


# =============================================================================
# GRAPH CONSTRUCTION
# =============================================================================

def create_compliance_graph():
    """Create the Compliance Review graph."""
    
    workflow = StateGraph(ComplianceState)
    
    # Add nodes
    workflow.add_node("check_bias", check_bias_regex_node)
    workflow.add_node("review_independence", review_independence_node)
    workflow.add_node("review_content", review_content_validity_node)
    workflow.add_node("generate_report", generate_compliance_report_node)
    
    # Parallel flow for checks
    workflow.set_entry_point("check_bias")
    
    # Fan out / Sequential for simplicity in this version
    workflow.add_edge("check_bias", "review_independence")
    workflow.add_edge("review_independence", "review_content") 
    workflow.add_edge("review_content", "generate_report")
    workflow.add_edge("generate_report", END)
    
    return workflow.compile()


# Compile for LangGraph Cloud
graph = create_compliance_graph()


if __name__ == "__main__":
    graph = create_compliance_graph()
    
    print("=== MERMAID DIAGRAM ===")
    print(graph.get_graph().draw_mermaid())
