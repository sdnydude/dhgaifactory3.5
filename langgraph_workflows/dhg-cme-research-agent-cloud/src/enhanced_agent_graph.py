"""
Enhanced CME Research Agent with Detailed Graph Visualization
Includes: parallel execution, conditional routing, rich metadata
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Literal
from datetime import datetime


# ============================================================================
# STATE DEFINITION
# ============================================================================

class ResearchState(TypedDict):
    """Enhanced state with detailed tracking"""
    
    # Input parameters
    topic: str
    therapeutic_area: str
    query_type: Literal["gap_analysis", "evidence_review", "guideline_update", "emerging_research"]
    target_audience: str
    date_range_years: int
    
    # Data collection results (parallel)
    pubmed_results: List[dict]
    pubmed_count: int
    perplexity_results: List[dict]
    perplexity_count: int
    guideline_results: List[dict]
    guideline_count: int
    
    # Analysis results
    evidence_graded: List[dict]
    evidence_summary: dict
    gaps_identified: List[dict]
    gap_count: int
    
    # Synthesis
    key_findings: List[str]
    synthesis_text: str
    citations: List[dict]
    
    # Output
    formatted_output: str
    output_format: str
    
    # Metadata
    processing_time: float
    model_used: str
    total_cost: float
    
    # Flow control
    current_phase: str
    errors: List[str]


# ============================================================================
# NODE FUNCTIONS
# ============================================================================

def initialize_research(state: ResearchState) -> ResearchState:
    """Initialize research parameters and validate input"""
    state["current_phase"] = "initialization"
    state["errors"] = []
    state["processing_time"] = 0.0
    return state


def route_query_type(state: ResearchState) -> str:
    """Route to appropriate research strategy based on query type"""
    query_type = state.get("query_type", "evidence_review")
    
    routing_map = {
        "gap_analysis": "gap_focused_search",
        "evidence_review": "comprehensive_search",
        "guideline_update": "guideline_focused_search",
        "emerging_research": "recent_research_search"
    }
    
    return routing_map.get(query_type, "comprehensive_search")


def comprehensive_search(state: ResearchState) -> ResearchState:
    """Trigger all parallel search paths"""
    state["current_phase"] = "comprehensive_search"
    # This will fan out to pubmed, perplexity, and guidelines
    return state


def search_pubmed(state: ResearchState) -> ResearchState:
    """Search PubMed for peer-reviewed literature"""
    state["current_phase"] = "pubmed_search"
    # Implementation would go here
    state["pubmed_results"] = []
    state["pubmed_count"] = 0
    return state


def search_perplexity(state: ResearchState) -> ResearchState:
    """Search current practice patterns via Perplexity"""
    state["current_phase"] = "perplexity_search"
    # Implementation would go here
    state["perplexity_results"] = []
    state["perplexity_count"] = 0
    return state


def search_guidelines(state: ResearchState) -> ResearchState:
    """Search clinical practice guidelines"""
    state["current_phase"] = "guideline_search"
    # Implementation would go here
    state["guideline_results"] = []
    state["guideline_count"] = 0
    return state


def grade_evidence(state: ResearchState) -> ResearchState:
    """Grade evidence using GRADE methodology"""
    state["current_phase"] = "evidence_grading"
    # Implementation would go here
    state["evidence_graded"] = []
    state["evidence_summary"] = {}
    return state


def identify_gaps(state: ResearchState) -> ResearchState:
    """Identify clinical practice gaps"""
    state["current_phase"] = "gap_identification"
    # Implementation would go here
    state["gaps_identified"] = []
    state["gap_count"] = 0
    return state


def synthesize_findings(state: ResearchState) -> ResearchState:
    """Synthesize all findings into coherent narrative"""
    state["current_phase"] = "synthesis"
    # Implementation would go here
    state["key_findings"] = []
    state["synthesis_text"] = ""
    return state


def format_output(state: ResearchState) -> ResearchState:
    """Format output based on requested format"""
    state["current_phase"] = "formatting"
    output_format = state.get("output_format", "cme_proposal")
    
    # Use template renderer
    from templates import render_template, TemplateType
    
    try:
        template_type = TemplateType(output_format)
        state["formatted_output"] = render_template(template_type, state)
    except ValueError:
        state["formatted_output"] = str(state)
        state["errors"].append(f"Unknown output format: {output_format}")
    
    return state


def finalize_research(state: ResearchState) -> ResearchState:
    """Finalize research and calculate metrics"""
    state["current_phase"] = "complete"
    # Calculate total processing time, cost, etc.
    return state


# ============================================================================
# GRAPH CONSTRUCTION
# ============================================================================

def create_enhanced_graph():
    """Create enhanced research graph with detailed visualization"""
    
    workflow = StateGraph(ResearchState)
    
    # Phase 1: Initialization
    workflow.add_node("initialize", initialize_research, metadata={
        "phase": "initialization",
        "description": "Initialize research parameters",
        "icon": "🚀",
        "color": "#3498DB",
        "estimated_time": "1s"
    })
    
    workflow.add_node("route", route_query_type, metadata={
        "phase": "routing",
        "description": "Route to appropriate strategy",
        "icon": "🔀",
        "color": "#9B59B6",
        "decision_point": True
    })
    
    # Phase 2: Data Collection (Parallel)
    workflow.add_node("comprehensive_search", comprehensive_search, metadata={
        "phase": "data_collection",
        "description": "Trigger parallel searches",
        "icon": "🔍",
        "color": "#1ABC9C",
        "fan_out": True
    })
    
    workflow.add_node("pubmed", search_pubmed, metadata={
        "phase": "data_collection",
        "description": "Search PubMed database",
        "icon": "📚",
        "color": "#4A90E2",
        "data_source": "PubMed",
        "estimated_time": "5-10s"
    })
    
    workflow.add_node("perplexity", search_perplexity, metadata={
        "phase": "data_collection",
        "description": "Search current practice",
        "icon": "🔍",
        "color": "#50C878",
        "data_source": "Perplexity",
        "estimated_time": "3-5s"
    })
    
    workflow.add_node("guidelines", search_guidelines, metadata={
        "phase": "data_collection",
        "description": "Search clinical guidelines",
        "icon": "📋",
        "color": "#F5A623",
        "data_source": "Guidelines",
        "estimated_time": "3-5s"
    })
    
    # Phase 3: Analysis
    workflow.add_node("grade", grade_evidence, metadata={
        "phase": "analysis",
        "description": "Grade evidence quality (GRADE)",
        "icon": "⭐",
        "color": "#9013FE",
        "methodology": "GRADE",
        "estimated_time": "10-15s"
    })
    
    workflow.add_node("gaps", identify_gaps, metadata={
        "phase": "analysis",
        "description": "Identify practice gaps",
        "icon": "🎯",
        "color": "#E74C3C",
        "estimated_time": "5-10s"
    })
    
    # Phase 4: Synthesis
    workflow.add_node("synthesize", synthesize_findings, metadata={
        "phase": "synthesis",
        "description": "Synthesize findings",
        "icon": "🧬",
        "color": "#16A085",
        "estimated_time": "15-20s"
    })
    
    # Phase 5: Output
    workflow.add_node("format", format_output, metadata={
        "phase": "output",
        "description": "Format final output",
        "icon": "📄",
        "color": "#34495E",
        "estimated_time": "2-3s"
    })
    
    workflow.add_node("finalize", finalize_research, metadata={
        "phase": "finalization",
        "description": "Finalize and calculate metrics",
        "icon": "✅",
        "color": "#27AE60",
        "estimated_time": "1s"
    })
    
    # ========================================================================
    # EDGES (Flow Control)
    # ========================================================================
    
    # Entry point
    workflow.set_entry_point("initialize")
    
    # Initialization → Routing
    workflow.add_edge("initialize", "route")
    
    # Conditional routing based on query type
    workflow.add_conditional_edges(
        "route",
        route_query_type,
        {
            "gap_focused_search": "gaps",
            "comprehensive_search": "comprehensive_search",
            "guideline_focused_search": "guidelines",
            "recent_research_search": "pubmed"
        }
    )
    
    # Comprehensive search fans out to parallel searches
    workflow.add_edge("comprehensive_search", "pubmed")
    workflow.add_edge("comprehensive_search", "perplexity")
    workflow.add_edge("comprehensive_search", "guidelines")
    
    # Parallel searches converge to evidence grading
    workflow.add_edge("pubmed", "grade")
    workflow.add_edge("perplexity", "grade")
    workflow.add_edge("guidelines", "grade")
    
    # Sequential analysis flow
    workflow.add_edge("grade", "gaps")
    workflow.add_edge("gaps", "synthesize")
    
    # Output flow
    workflow.add_edge("synthesize", "format")
    workflow.add_edge("format", "finalize")
    workflow.add_edge("finalize", END)
    
    # Compile graph
    return workflow.compile()


# ============================================================================
# VISUALIZATION
# ============================================================================

if __name__ == "__main__":
    graph = create_enhanced_graph()
    
    # Generate Mermaid diagram
    mermaid = graph.get_graph().draw_mermaid()
    print("=== MERMAID DIAGRAM ===")
    print(mermaid)
    print("\n")
    
    # Generate ASCII representation
    print("=== GRAPH STRUCTURE ===")
    print(graph.get_graph())
