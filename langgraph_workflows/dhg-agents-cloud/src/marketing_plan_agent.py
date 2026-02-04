"""
Marketing Plan Agent - Agent #9
================================
Creates comprehensive audience generation strategy with multi-channel
marketing plan, budget allocation, and timeline.

LangGraph Cloud Ready:
- Produces complete marketing plan with budget and projections
- Input from: Learning Objectives Agent, Needs Assessment Agent
- Output to: Grant Writer Agent
"""

import os
import re
import json
import operator
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


# =============================================================================
# CONFIGURATION
# =============================================================================

# Channel characteristics
CHANNEL_DATA = {
    "email_house": {"reach": "Medium", "conversion": 0.04, "cost": "Low"},
    "email_rented": {"reach": "High", "conversion": 0.01, "cost": "Medium"},
    "society": {"reach": "Medium", "conversion": 0.03, "cost": "Medium"},
    "journal_ad": {"reach": "High", "conversion": 0.002, "cost": "High"},
    "social_organic": {"reach": "Low", "conversion": 0.002, "cost": "Low"},
    "social_paid": {"reach": "Medium", "conversion": 0.005, "cost": "Medium"},
    "conference": {"reach": "Low", "conversion": 0.05, "cost": "High"},
    "peer_referral": {"reach": "Low", "conversion": 0.08, "cost": "Low"},
    "aggregators": {"reach": "Medium", "conversion": 0.008, "cost": "Medium"}
}

# Cost per registration benchmarks
CPR_BENCHMARKS = {
    "live_event": {"min": 50, "max": 150, "typical": 100},
    "online_activity": {"min": 15, "max": 50, "typical": 30}
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class MarketingPlanState(TypedDict):
    # === INPUT (from upstream agents) ===
    learning_objectives_report: Optional[Dict[str, Any]]
    needs_assessment_document: Optional[str]
    
    # From intake form
    target_audience: str
    practice_settings: Optional[List[str]]
    geographic_focus: Optional[str]
    estimated_reach: int
    marketing_budget: Optional[float]
    marketing_channels: Optional[List[str]]
    launch_date: Optional[str]
    therapeutic_area: str
    disease_state: str
    educational_format: Optional[str]
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific data
    audience_profile: Dict[str, Any]
    key_messages: Dict[str, Any]
    channel_strategy: Dict[str, Any]
    budget_allocation: Dict[str, Any]
    timeline: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    
    # === OUTPUT ===
    marketing_report: Dict[str, Any]
    marketing_document: str
    
    # === METADATA ===
    total_budget: float
    projected_reach: int
    cost_per_registration: float
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client with cost tracking."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015
    
    @traceable(name="marketing_plan_llm_call", run_type="llm")
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
        
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + \
               (output_tokens / 1000 * self.cost_per_1k_output)
        
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

MARKETING_SYSTEM_PROMPT = """You are a healthcare marketing strategist developing an audience generation plan for a continuing medical education activity. Your plan must:

1. TARGETED: Focus resources on channels that reach the specific audience
2. REALISTIC: Budget and reach projections must be achievable
3. COMPLIANT: Adhere to CME marketing regulations
4. INTEGRATED: Channels should work together, not in isolation
5. MEASURABLE: Include KPIs and tracking mechanisms

CHANNEL SELECTION PRINCIPLES:
- Society partnerships reach engaged, relevant audiences
- Email remains highest-converting channel for HCP education
- Social media works for awareness but low direct conversion
- Journal advertising builds credibility but high cost-per-registration
- Peer-to-peer outreach is effective but resource-intensive

BUDGET ALLOCATION GUIDELINES:
- Cost per registration typically $50-150 for live events
- Cost per registration typically $15-50 for online activities
- Allocate 60-70% to highest-performing channels
- Reserve 10-15% for optimization/contingency

COMPLIANCE REQUIREMENTS:
- Marketing must be independent of supporter
- No promotion of specific products
- Educational content must be foregrounded
- Appropriate disclosures required"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="develop_audience_profile_node", run_type="chain")
async def develop_audience_profile_node(state: MarketingPlanState) -> dict:
    """Develop detailed audience profile."""
    
    audience = state.get("target_audience", "")
    settings = state.get("practice_settings", [])
    geographic = state.get("geographic_focus", "United States")
    estimated_reach = state.get("estimated_reach", 500)
    disease = state.get("disease_state", "")
    
    system = f"""{MARKETING_SYSTEM_PROMPT}

You are developing an AUDIENCE PROFILE. Return a JSON object:
{{
    "primary_audience": {{
        "specialty": "Primary specialty target",
        "practice_settings": ["Academic", "Community", "Private practice"],
        "geographic_scope": "National/Regional",
        "estimated_universe": 50000
    }},
    "secondary_audiences": [
        {{
            "segment": "Secondary specialty or role",
            "rationale": "Why include this segment",
            "estimated_size": 20000
        }}
    ],
    "audience_insights": {{
        "key_motivators": [
            "Board certification maintenance",
            "Quality improvement requirements",
            "Clinical uncertainty in this area"
        ],
        "barriers_to_engagement": [
            "Time constraints",
            "Competing educational offerings"
        ],
        "preferred_channels": ["Email", "Society communications", "Journal alerts"],
        "optimal_timing": "Early morning or evening, weekdays preferred"
    }}
}}"""
    
    prompt = f"""Develop audience profile for {disease} CME.
Target audience: {audience}
Practice settings: {json.dumps(settings) if settings else "Not specified"}
Geographic focus: {geographic}
Target reach: {estimated_reach}

Create a detailed profile that will inform channel selection and messaging.

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "audience_profile"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            audience_profile = json.loads(json_match.group())
        else:
            audience_profile = {}
    except json.JSONDecodeError:
        audience_profile = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "audience_profile": audience_profile,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="craft_key_messages_node", run_type="chain")
async def craft_key_messages_node(state: MarketingPlanState) -> dict:
    """Craft key marketing messages."""
    
    disease = state.get("disease_state", "")
    audience = state.get("target_audience", "")
    objectives = state.get("learning_objectives_report", {}).get("objectives", [])
    
    system = f"""{MARKETING_SYSTEM_PROMPT}

You are crafting KEY MESSAGES for marketing. Return a JSON object:
{{
    "primary_message": "Main value proposition in 20 words or fewer",
    "supporting_messages": [
        {{
            "message": "Supporting point 1",
            "target_segment": "Primary care physicians"
        }},
        {{
            "message": "Supporting point 2",
            "target_segment": "Specialists"
        }}
    ],
    "call_to_action": "Register now to...",
    "compliance_considerations": "Educational focus emphasized, no product promotion"
}}

Messages must:
- Lead with educational value
- Not promote specific products
- Highlight clinical relevance"""
    
    # Extract objective themes
    obj_themes = [o.get("objective_text", "")[:100] for o in objectives[:3]]
    
    prompt = f"""Craft key marketing messages for {disease} CME targeting {audience}.

LEARNING OBJECTIVES (for message alignment):
{json.dumps(obj_themes, indent=2)}

Create compelling, compliant messages that:
1. Emphasize educational value
2. Address clinical needs
3. Motivate registration
4. Maintain CME compliance

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "key_messages"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            key_messages = json.loads(json_match.group())
        else:
            key_messages = {}
    except json.JSONDecodeError:
        key_messages = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "key_messages": key_messages,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="develop_channel_strategy_node", run_type="chain")
async def develop_channel_strategy_node(state: MarketingPlanState) -> dict:
    """Develop multi-channel marketing strategy."""
    
    audience = state.get("target_audience", "")
    audience_profile = state.get("audience_profile", {})
    budget = state.get("marketing_budget", 50000)
    reach_target = state.get("estimated_reach", 500)
    preferred_channels = state.get("marketing_channels", [])
    disease = state.get("disease_state", "")
    format_type = state.get("educational_format", "Live symposium")
    
    # Determine if live or online for CPR benchmark
    is_live = "live" in format_type.lower() if format_type else True
    cpr_benchmark = CPR_BENCHMARKS["live_event" if is_live else "online_activity"]["typical"]
    
    system = f"""{MARKETING_SYSTEM_PROMPT}

You are developing a CHANNEL STRATEGY. Return a JSON object:
{{
    "channels": [
        {{
            "channel_name": "Society Partnership (e.g., ACC)",
            "channel_type": "society",
            "description": "Partnership with major society for member outreach",
            "target_audience_fit": "Why this channel reaches the audience",
            "tactics": [
                {{
                    "tactic": "Website activity listing",
                    "timing": "Weeks 1-12",
                    "cost": 5000,
                    "expected_reach": 15000,
                    "expected_conversion": 0.015
                }}
            ],
            "total_channel_budget": 17000,
            "projected_registrations": 195
        }}
    ],
    "channel_mix_rationale": "Why these channels were selected...",
    "integration_strategy": "How channels work together..."
}}

CHANNEL CONVERSION RATES (use these for projections):
- Email (house list): 3-5%
- Email (rented list): 0.5-1.5%
- Society partnership: 2-4%
- Journal advertising: 0.1-0.3%
- Social media paid: 0.3-0.8%
- CME aggregators: 0.5-1%"""
    
    preferred_context = ""
    if preferred_channels:
        preferred_context = f"\nPREFERRED CHANNELS (prioritize): {', '.join(preferred_channels)}"
    
    prompt = f"""Develop channel strategy for {disease} CME.
Target audience: {audience}
Budget: ${budget:,.0f}
Reach target: {reach_target} registrations
Format: {format_type}
Target CPR: ${cpr_benchmark}
{preferred_context}

AUDIENCE INSIGHTS:
Preferred channels: {json.dumps(audience_profile.get('audience_insights', {}).get('preferred_channels', []))}
Key motivators: {json.dumps(audience_profile.get('audience_insights', {}).get('key_motivators', []))}

Select 3-5 channels that will achieve the reach target within budget. Be specific about tactics, costs, and projected outcomes.

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "channel_strategy"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            channel_strategy = json.loads(json_match.group())
        else:
            channel_strategy = {"channels": []}
    except json.JSONDecodeError:
        channel_strategy = {"channels": []}
    
    # Calculate total projected registrations
    total_projected = sum(
        c.get("projected_registrations", 0)
        for c in channel_strategy.get("channels", [])
    )
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "channel_strategy": channel_strategy,
        "projected_reach": total_projected,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="create_budget_allocation_node", run_type="chain")
async def create_budget_allocation_node(state: MarketingPlanState) -> dict:
    """Create detailed budget allocation."""
    
    budget = state.get("marketing_budget", 50000)
    channel_strategy = state.get("channel_strategy", {})
    projected_reach = state.get("projected_reach", 500)
    
    # Extract channel budgets
    channels = channel_strategy.get("channels", [])
    allocation_by_channel = []
    total_allocated = 0
    
    for channel in channels:
        channel_budget = channel.get("total_channel_budget", 0)
        total_allocated += channel_budget
        allocation_by_channel.append({
            "channel": channel.get("channel_name", "Unknown"),
            "budget": channel_budget,
            "percentage": (channel_budget / budget * 100) if budget > 0 else 0
        })
    
    # Calculate contingency
    contingency = max(0, budget - total_allocated)
    if contingency > 0:
        allocation_by_channel.append({
            "channel": "Contingency/Optimization",
            "budget": contingency,
            "percentage": (contingency / budget * 100) if budget > 0 else 0
        })
    
    # Calculate cost per registration
    cpr = budget / projected_reach if projected_reach > 0 else 0
    
    budget_allocation = {
        "total_budget": budget,
        "allocation_by_channel": allocation_by_channel,
        "allocation_by_phase": [
            {"phase": "Pre-Launch", "budget": budget * 0.1, "activities": ["Asset development", "Partnership setup"]},
            {"phase": "Launch (Weeks 1-4)", "budget": budget * 0.4, "activities": ["Initial activations", "Email campaigns"]},
            {"phase": "Sustain (Weeks 5-10)", "budget": budget * 0.35, "activities": ["Ongoing promotion", "Optimization"]},
            {"phase": "Close (Weeks 11-12)", "budget": budget * 0.15, "activities": ["Final push", "Reminder campaigns"]}
        ],
        "contingency": contingency,
        "cost_per_registration_target": round(cpr, 2)
    }
    
    return {
        "budget_allocation": budget_allocation,
        "total_budget": budget,
        "cost_per_registration": cpr,
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="build_timeline_node", run_type="chain")
async def build_timeline_node(state: MarketingPlanState) -> dict:
    """Build marketing timeline."""
    
    launch_date = state.get("launch_date", "TBD")
    channel_strategy = state.get("channel_strategy", {})
    
    system = f"""{MARKETING_SYSTEM_PROMPT}

You are building a MARKETING TIMELINE. Return a JSON object:
{{
    "phases": [
        {{
            "phase_name": "Pre-Launch",
            "start_date": "Week -4",
            "end_date": "Week 0",
            "activities": [
                {{
                    "activity": "Finalize creative assets",
                    "timing": "Week -4",
                    "responsible_party": "Marketing team"
                }}
            ]
        }}
    ],
    "key_milestones": [
        {{
            "milestone": "All partnerships confirmed",
            "date": "Week -2",
            "success_criteria": "Signed agreements with all society partners"
        }}
    ]
}}"""
    
    channels = [c.get("channel_name") for c in channel_strategy.get("channels", [])]
    
    prompt = f"""Build marketing timeline for CME launch.
Launch date: {launch_date}
Campaign duration: 12 weeks

CHANNELS TO ACTIVATE:
{json.dumps(channels, indent=2)}

Create a timeline with:
1. Pre-launch phase (4 weeks before)
2. Launch phase (weeks 1-3)
3. Sustain phase (weeks 4-10)
4. Close phase (weeks 11-12)

Include specific activities and milestones.

Return ONLY valid JSON."""

    result = await llm.generate(system, prompt, {"step": "timeline"})
    
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            timeline = json.loads(json_match.group())
        else:
            timeline = {}
    except json.JSONDecodeError:
        timeline = {}
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "timeline": timeline,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


@traceable(name="define_metrics_node", run_type="chain")
async def define_metrics_node(state: MarketingPlanState) -> dict:
    """Define performance metrics and KPIs."""
    
    channel_strategy = state.get("channel_strategy", {})
    budget = state.get("total_budget", 50000)
    projected_reach = state.get("projected_reach", 500)
    
    performance_metrics = {
        "kpis": [
            {
                "metric": "Total Registrations",
                "target": str(projected_reach),
                "measurement_method": "Registration system tracking"
            },
            {
                "metric": "Cost Per Registration",
                "target": f"${budget/projected_reach:.2f}" if projected_reach > 0 else "N/A",
                "measurement_method": "Total spend / registrations"
            },
            {
                "metric": "Email Open Rate",
                "target": "20-25%",
                "measurement_method": "Email platform analytics"
            },
            {
                "metric": "Email Click-Through Rate",
                "target": "3-5%",
                "measurement_method": "Email platform analytics"
            },
            {
                "metric": "Landing Page Conversion",
                "target": "15-20%",
                "measurement_method": "Web analytics"
            },
            {
                "metric": "Channel Attribution",
                "target": "Track by UTM",
                "measurement_method": "Google Analytics, registration source"
            }
        ],
        "tracking_plan": "All campaigns will use UTM parameters for attribution. Weekly performance reports will be generated. A central dashboard will track registrations by channel.",
        "optimization_triggers": "Underperforming channels (below 50% of projected conversions at week 4) will have budget reallocated to higher performers."
    }
    
    return {
        "performance_metrics": performance_metrics,
        "total_tokens": state.get("total_tokens", 0),
        "total_cost": state.get("total_cost", 0.0)
    }


@traceable(name="assemble_marketing_report_node", run_type="chain")
async def assemble_marketing_report_node(state: MarketingPlanState) -> dict:
    """Assemble the final marketing report."""
    
    channel_strategy = state.get("channel_strategy", {})
    budget_allocation = state.get("budget_allocation", {})
    
    report = {
        "metadata": {
            "agent_version": "2.0",
            "execution_timestamp": datetime.now().isoformat(),
            "total_budget": state.get("total_budget", 0),
            "projected_reach": state.get("projected_reach", 0),
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        "executive_summary": {
            "strategy_overview": f"Multi-channel marketing strategy targeting {state.get('target_audience', 'healthcare professionals')} through {len(channel_strategy.get('channels', []))} integrated channels.",
            "key_channels": [c.get("channel_name") for c in channel_strategy.get("channels", [])[:4]],
            "projected_outcomes": f"{state.get('projected_reach', 0)} registrations at ${state.get('cost_per_registration', 0):.2f}/registration",
            "budget_summary": f"${state.get('total_budget', 0):,.0f} total marketing investment"
        },
        "target_audience_profile": state.get("audience_profile", {}),
        "key_messages": state.get("key_messages", {}),
        "channel_strategy": channel_strategy,
        "budget_allocation": budget_allocation,
        "timeline": state.get("timeline", {}),
        "performance_metrics": state.get("performance_metrics", {}),
        "compliance_and_independence": {
            "disclosure_requirements": "All marketing materials will include appropriate educational grant disclosure language.",
            "content_restrictions": "No mention of specific branded products. Educational content and learning objectives emphasized.",
            "regulatory_considerations": "All communications comply with ACCME Standards for Integrity and Independence in Accredited CE."
        }
    }
    
    return {
        "marketing_report": report,
        "messages": [HumanMessage(content=f"Marketing plan complete: ${state.get('total_budget', 0):,.0f} budget targeting {state.get('projected_reach', 0)} registrations")]
    }


@traceable(name="render_marketing_document_node", run_type="chain")
async def render_marketing_document_node(state: MarketingPlanState) -> dict:
    """Render the marketing plan as a readable document."""
    
    disease = state.get("disease_state", "")
    report = state.get("marketing_report", {})
    
    system = """You are a healthcare marketing strategist writing a marketing plan document.

FORMATTING RULES:
- Use markdown headers
- Present budget as tables
- Include channel details
- Show timeline visually
- Focus on actionable tactics

STRUCTURE:
1. Executive Summary
2. Target Audience Profile
3. Key Messages
4. Channel Strategy (with tactics and costs)
5. Budget Allocation
6. Timeline
7. Performance Metrics
8. Compliance

Write in professional marketing language."""
    
    prompt = f"""Create a marketing plan document for {disease} CME.

MARKETING PLAN DATA:
{json.dumps(report, indent=2)[:15000]}

Present as a complete, actionable marketing plan."""

    result = await llm.generate(system, prompt, {"step": "render_document"})
    
    document = result["content"]
    
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "marketing_document": document,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_marketing_plan_graph() -> StateGraph:
    """Create the Marketing Plan Agent graph."""
    
    graph = StateGraph(MarketingPlanState)
    
    # Add nodes
    graph.add_node("develop_audience", develop_audience_profile_node)
    graph.add_node("craft_messages", craft_key_messages_node)
    graph.add_node("develop_channels", develop_channel_strategy_node)
    graph.add_node("create_budget", create_budget_allocation_node)
    graph.add_node("build_timeline", build_timeline_node)
    graph.add_node("define_metrics", define_metrics_node)
    graph.add_node("assemble_report", assemble_marketing_report_node)
    graph.add_node("render_document", render_marketing_document_node)
    
    # Flow: sequential marketing plan development
    graph.set_entry_point("develop_audience")
    
    graph.add_edge("develop_audience", "craft_messages")
    graph.add_edge("craft_messages", "develop_channels")
    graph.add_edge("develop_channels", "create_budget")
    graph.add_edge("create_budget", "build_timeline")
    graph.add_edge("build_timeline", "define_metrics")
    graph.add_edge("define_metrics", "assemble_report")
    graph.add_edge("assemble_report", "render_document")
    graph.add_edge("render_document", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_marketing_plan_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        test_state = {
            "therapeutic_area": "cardiology",
            "disease_state": "heart failure",
            "target_audience": "cardiologists and primary care physicians",
            "practice_settings": ["Academic", "Community"],
            "geographic_focus": "United States",
            "estimated_reach": 500,
            "marketing_budget": 50000,
            "marketing_channels": ["Email", "Society partnerships"],
            "launch_date": "April 1, 2026",
            "educational_format": "Live symposium",
            "messages": [],
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== MARKETING PLAN RESULT ===")
        print(f"Total budget: ${result.get('total_budget', 0):,.0f}")
        print(f"Projected reach: {result.get('projected_reach', 0)}")
        print(f"Cost per registration: ${result.get('cost_per_registration', 0):.2f}")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
        
        report = result.get("marketing_report", {})
        channels = report.get("channel_strategy", {}).get("channels", [])
        print(f"\n=== CHANNELS ===")
        for c in channels:
            print(f"- {c.get('channel_name', 'Unknown')}: ${c.get('total_channel_budget', 0):,.0f}")
    
    asyncio.run(test())
