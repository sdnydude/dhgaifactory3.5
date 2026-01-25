"""
Test script for output_format parameter
"""
import asyncio
import sys
sys.path.insert(0, "./src")

from templates.renderer import render_template, TemplateType

# Mock research data
mock_data = {
    "topic": "Chronic Cough Management",
    "therapeutic_area": "pulmonology",
    "synthesis": """Recent evidence suggests that chronic cough refractory to standard treatments 
    may benefit from neuromodulators and speech therapy interventions. Clinical practice shows 
    significant gaps in systematic assessment and treatment escalation.""",
    "clinical_gaps": [
        "Delayed referral to specialists for refractory cases",
        "Inconsistent use of validated cough assessment tools",
        "Limited awareness of neuromodulator efficacy"
    ],
    "key_findings": [
        "75% of chronic cough cases improve with multimodal therapy",
        "Gabapentin shows 50% reduction in cough frequency in RCTs",
        "Speech pathology intervention reduces cough severity by 40%"
    ],
    "validated_citations": [
        {
            "title": "Gabapentin for chronic cough: a randomised trial",
            "journal": "Lancet Respir Med",
            "year": "2022",
            "pmid": "12345678"
        },
        {
            "title": "Speech therapy for chronic refractory cough",
            "journal": "Thorax",
            "year": "2021",
            "pmid": "87654321"
        }
    ],
    "model_used": "claude-sonnet-4",
    "total_tokens": 12500,
    "total_cost": 0.156
}

async def test_formats():
    """Test all output formats"""
    formats = ["json", "cme_proposal", "podcast_script", "gap_report", "powerpoint_outline"]
    
    for fmt in formats:
        sep = "=" * 70
        print(f"\n{sep}")
        print(f"Testing format: {fmt}")
        print(f"{sep}\n")
        
        if fmt == "json":
            import json
            output = json.dumps(mock_data, indent=2)
        else:
            template_type = TemplateType(fmt)
            output = render_template(template_type, mock_data)
        
        preview = output[:500] + "..." if len(output) > 500 else output
        print(preview)
        print(f"\nOK: {fmt} format rendered successfully ({len(output)} chars)\n")

if __name__ == "__main__":
    asyncio.run(test_formats())
