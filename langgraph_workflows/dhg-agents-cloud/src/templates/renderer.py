  # Simplified Template Renderer - Copy this to server
# Location: /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-cme-research-agent-cloud/src/templates/renderer.py

from enum import Enum
from typing import Dict, Any
from datetime import datetime
import json


class TemplateType(str, Enum):
    JSON = "json"
    CME_PROPOSAL = "cme_proposal"
    PODCAST_SCRIPT = "podcast_script"
    GAP_REPORT = "gap_report"
    POWERPOINT_OUTLINE = "powerpoint_outline"


def render_template(template_type: TemplateType, data: Dict[str, Any]) -> str:
    """Render agent output using specified template"""
    if template_type == TemplateType.JSON:
        return json.dumps(data, indent=2)
    elif template_type == TemplateType.CME_PROPOSAL:
        return render_cme_proposal(data)
    elif template_type == TemplateType.PODCAST_SCRIPT:
        return render_podcast_script(data)
    elif template_type == TemplateType.GAP_REPORT:
        return render_gap_report(data)
    elif template_type == TemplateType.POWERPOINT_OUTLINE:
        return render_powerpoint_outline(data)
    else:
        raise ValueError(f"Unknown template type: {template_type}")


def render_cme_proposal(data: Dict[str, Any]) -> str:
    """Render CME Activity Proposal"""
    topic = data.get("topic", "Unknown Topic")
    gaps = data.get("clinical_gaps", [])
    findings = data.get("key_findings", [])
    citations = data.get("validated_citations", [])
    synthesis = data.get("synthesis", "")
    
    output = f"""# CME Activity Proposal: {topic}

**Date:** {datetime.now().strftime("%B %d, %Y")}

## Educational Need

Current clinical practice demonstrates {len(gaps)} critical gaps:

"""
    for i, gap in enumerate(gaps, 1):
        output += f"{i}. {gap}\n"
    
    output += f"""
## Content Outline

{synthesis}

## Key Evidence

"""
    for i, finding in enumerate(findings, 1):
        output += f"{i}. {finding}\n"
    
    output += f"""
## References ({len(citations)} citations)

"""
    for i, cit in enumerate(citations[:10], 1):
        ama = cit.get("ama_format", cit.get("title", "Citation"))
        output += f"{i}. {ama}\n"
    
    return output


def render_podcast_script(data: Dict[str, Any]) -> str:
    """Render Podcast Script"""
    topic = data.get("topic", "Unknown Topic")
    gaps = data.get("clinical_gaps", [])
    findings = data.get("key_findings", [])
    
    output = f"""# Podcast Script: {topic}

## Opening

Welcome to DHG CME Podcast. Today: {topic}

## Educational Gap

"""
    for gap in gaps[:2]:
        output += f"- {gap}\n"
    
    output += """
## Key Findings

"""
    for finding in findings:
        output += f"- {finding}\n"
    
    output += """
## Closing

Thank you for listening. Visit our website to claim CME credit.
"""
    return output


def render_gap_report(data: Dict[str, Any]) -> str:
    """Render Gap Analysis Report"""
    topic = data.get("topic", "Unknown Topic")
    gaps = data.get("clinical_gaps", [])
    findings = data.get("key_findings", [])
    citations = data.get("validated_citations", [])
    
    output = f"""# Clinical Practice Gap Analysis

**Topic:** {topic}
**Date:** {datetime.now().strftime("%B %d, %Y")}

## Identified Gaps ({len(gaps)} total)

"""
    for i, gap in enumerate(gaps, 1):
        priority = "High" if i <= 2 else "Medium"
        output += f"### Gap #{i}: {gap}\n**Priority:** {priority}\n\n"
    
    output += f"""
## Supporting Evidence

"""
    for finding in findings:
        output += f"- {finding}\n"
    
    output += f"""
## Evidence Base: {len(citations)} citations
"""
    return output


def render_powerpoint_outline(data: Dict[str, Any]) -> str:
    """Render PowerPoint Outline"""
    topic = data.get("topic", "Unknown Topic")
    gaps = data.get("clinical_gaps", [])
    findings = data.get("key_findings", [])
    
    output = f"""# PowerPoint Outline: {topic}

## Slide 1: Title
{topic}

## Slide 2: Learning Objectives
"""
    for i, gap in enumerate(gaps[:4], 1):
        output += f"{i}. Describe {gap.lower()}\n"
    
    output += """
## Slides 3-5: Evidence Review
[Content from synthesis]

## Slide 6: Key Findings
"""
    for finding in findings:
        output += f"- {finding}\n"
    
    output += """
## Slide 7: References
[Citations]
"""
    return output
