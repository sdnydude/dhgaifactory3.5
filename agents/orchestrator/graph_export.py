"""
Export compiled graph for LangSmith Studio visualization
"""
from langgraph.graph import StateGraph, END
from typing import Dict, Any, List, Optional, TypedDict

class GraphState(TypedDict):
    task_id: str
    topic: str
    compliance_mode: str
    task_type: str
    messages: List[Dict[str, Any]]
    research_data: Optional[Dict[str, Any]]
    medical_content: Optional[str]
    curriculum: Optional[Dict[str, Any]]
    outcomes: Optional[Dict[str, Any]]
    compliance_report: Optional[Dict[str, Any]]
    final_deliverable: Optional[Dict[str, Any]]
    current_agent: str
    status: str
    errors: List[str]
    metadata: Dict[str, Any]

def build_graph():
    """Build the DHG agent workflow graph"""
    workflow = StateGraph(GraphState)
    
    def router(state): return {**state, "current_agent": "router"}
    def research_agent(state): return {**state, "current_agent": "research"}
    def medical_llm_agent(state): return {**state, "current_agent": "medical_llm"}
    def curriculum_agent(state): return {**state, "current_agent": "curriculum"}
    def outcomes_agent(state): return {**state, "current_agent": "outcomes"}
    def qa_compliance_agent(state): return {**state, "current_agent": "qa_compliance"}
    def finalize(state): return {**state, "current_agent": "finalize", "status": "complete"}
    
    workflow.add_node("router", router)
    workflow.add_node("research_agent", research_agent)
    workflow.add_node("medical_llm_agent", medical_llm_agent)
    workflow.add_node("curriculum_agent", curriculum_agent)
    workflow.add_node("outcomes_agent", outcomes_agent)
    workflow.add_node("qa_compliance_agent", qa_compliance_agent)
    workflow.add_node("finalize", finalize)
    
    workflow.set_entry_point("router")
    
    def route_task(state):
        task_type = state.get("task_type", "general")
        if task_type in ["needs_assessment", "cme_script"]:
            return "research"
        elif task_type in ["curriculum", "learning_objectives"]:
            return "curriculum"
        return "finalize"
    
    workflow.add_conditional_edges(
        "router",
        route_task,
        {"research": "research_agent", "curriculum": "curriculum_agent", "finalize": "finalize"}
    )
    
    workflow.add_edge("research_agent", "medical_llm_agent")
    workflow.add_edge("medical_llm_agent", "qa_compliance_agent")
    workflow.add_edge("curriculum_agent", "outcomes_agent")
    workflow.add_edge("outcomes_agent", "qa_compliance_agent")
    workflow.add_edge("qa_compliance_agent", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()

graph = build_graph()
