"""
DHG AI FACTORY - LANGGRAPH INTEGRATION
Graph-based agent orchestration with PostgreSQL persistence
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
import structlog
import httpx

from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
except ImportError:
    try:
        from langgraph_checkpoint_postgres import PostgresSaver
        AsyncPostgresSaver = None
    except ImportError:
        PostgresSaver = None
        AsyncPostgresSaver = None
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logger = structlog.get_logger()


class GraphState(TypedDict):
    """State for the agent graph"""
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


class DHGAgentGraph:
    """
    LangGraph-based orchestration for DHG AI Factory.
    
    Uses PostgreSQL checkpointing for state persistence,
    enabling resumable workflows and conversation history.
    """
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("REGISTRY_DB_URL")
        self.checkpointer = None
        self.graph = None
        self.compiled_graph = None
        self.logger = logger.bind(component="langgraph")
        self.http_client = None
        
        self.agent_urls = {
            "research": os.getenv("RESEARCH_URL", "http://research:8000"),
            "medical_llm": os.getenv("MEDICAL_LLM_URL", "http://medical-llm:8000"),
            "curriculum": os.getenv("CURRICULUM_URL", "http://curriculum:8000"),
            "outcomes": os.getenv("OUTCOMES_URL", "http://outcomes:8000"),
            "qa_compliance": os.getenv("QA_COMPLIANCE_URL", "http://qa-compliance:8000"),
        }
    
    async def _call_agent(self, agent_name: str, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Make HTTP call to a specialized agent"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=120.0)
        
        url = f"{self.agent_urls.get(agent_name, '')}/{endpoint}"
        try:
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error("agent_call_failed", agent=agent_name, endpoint=endpoint, error=str(e))
            return {"error": str(e), "agent": agent_name}
        
    async def initialize(self):
        """Initialize the graph with PostgreSQL checkpointer"""
        try:
            if self.db_url and AsyncPostgresSaver is not None:
                try:
                    # Use AsyncPostgresSaver for async graph operations
                    checkpointer_cm = AsyncPostgresSaver.from_conn_string(self.db_url)
                    # Enter the context manager if needed
                    if hasattr(checkpointer_cm, '__aenter__'):
                        self._checkpointer_cm = checkpointer_cm
                        self.checkpointer = await checkpointer_cm.__aenter__()
                    elif hasattr(checkpointer_cm, '__enter__'):
                        self._checkpointer_cm = checkpointer_cm
                        self.checkpointer = checkpointer_cm.__enter__()
                    else:
                        self.checkpointer = checkpointer_cm
                    self.logger.info("langgraph_postgres_connected", db_url=self.db_url[:50] + "...")
                except Exception as db_err:
                    self.logger.warning("langgraph_postgres_failed", error=str(db_err))
                    self.checkpointer = None
            else:
                self.logger.warning("langgraph_no_db", message="Running without persistence")
            
            self._build_graph()
            self.logger.info("langgraph_initialized")
            
        except Exception as e:
            self.logger.error("langgraph_init_failed", error=str(e))
            raise
    
    def _build_graph(self):
        """Build the agent workflow graph"""
        
        workflow = StateGraph(GraphState)
        
        workflow.add_node("router", self._route_task)
        workflow.add_node("research_agent", self._research_node)
        workflow.add_node("medical_llm_agent", self._medical_llm_node)
        workflow.add_node("curriculum_agent", self._curriculum_node)
        workflow.add_node("outcomes_agent", self._outcomes_node)
        workflow.add_node("qa_compliance_agent", self._qa_compliance_node)
        workflow.add_node("finalize", self._finalize_node)
        
        workflow.set_entry_point("router")
        
        workflow.add_conditional_edges(
            "router",
            self._determine_next_agent,
            {
                "research": "research_agent",
                "medical_llm": "medical_llm_agent",
                "curriculum": "curriculum_agent",
                "outcomes": "outcomes_agent",
                "qa_compliance": "qa_compliance_agent",
                "finalize": "finalize",
                "end": END
            }
        )
        
        workflow.add_edge("research_agent", "medical_llm_agent")
        workflow.add_edge("medical_llm_agent", "qa_compliance_agent")
        workflow.add_edge("curriculum_agent", "outcomes_agent")
        workflow.add_edge("outcomes_agent", "qa_compliance_agent")
        workflow.add_edge("qa_compliance_agent", "finalize")
        workflow.add_edge("finalize", END)
        
        if self.checkpointer:
            self.compiled_graph = workflow.compile(checkpointer=self.checkpointer)
        else:
            self.compiled_graph = workflow.compile()
        
        self.graph = workflow
        self.logger.info("langgraph_built", nodes=len(workflow.nodes))
    
    def _determine_next_agent(self, state: GraphState) -> str:
        """Determine the next agent based on task type and current state"""
        task_type = state.get("task_type", "general")
        current = state.get("current_agent", "")
        
        if current == "router":
            if task_type in ["needs_assessment", "cme_script", "gap_analysis"]:
                return "research"
            elif task_type in ["curriculum", "learning_objectives"]:
                return "curriculum"
            elif task_type == "business_strategy":
                return "finalize"
            else:
                return "research"
        
        return "finalize"
    
    async def _route_task(self, state: GraphState) -> GraphState:
        """Route the task to appropriate agents"""
        self.logger.info("routing_task", task_type=state.get("task_type"))
        
        return {
            **state,
            "current_agent": "router",
            "status": "routing",
            "metadata": {
                **state.get("metadata", {}),
                "routed_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _research_node(self, state: GraphState) -> GraphState:
        """Execute research agent - calls real research service"""
        self.logger.info("research_agent_executing", topic=state.get("topic"))
        
        payload = {
            "topic": state.get("topic"),
            "sources": ["pubmed", "cochrane", "clinical_trials"],
            "max_results": 20,
            "include_epidemiology": True,
            "include_guidelines": True
        }
        
        result = await self._call_agent("research", "research", payload)
        
        return {
            **state,
            "current_agent": "research",
            "status": "research_complete" if "error" not in result else "research_failed",
            "research_data": result,
            "errors": state.get("errors", []) + ([result.get("error")] if "error" in result else [])
        }
    
    async def _medical_llm_node(self, state: GraphState) -> GraphState:
        """Execute medical LLM agent - calls real medical-llm service"""
        self.logger.info("medical_llm_executing", topic=state.get("topic"))
        
        payload = {
            "task": state.get("task_type", "general"),
            "topic": state.get("topic"),
            "research_data": state.get("research_data"),
            "compliance_mode": state.get("compliance_mode", "auto"),
            "word_count_target": 500,
            "include_sdoh": True,
            "include_equity": True
        }
        
        result = await self._call_agent("medical_llm", "generate", payload)
        
        return {
            **state,
            "current_agent": "medical_llm",
            "status": "content_generated" if "error" not in result else "content_failed",
            "medical_content": result.get("content"),
            "errors": state.get("errors", []) + ([result.get("error")] if "error" in result else [])
        }
    
    async def _curriculum_node(self, state: GraphState) -> GraphState:
        """Execute curriculum agent - calls real curriculum service"""
        self.logger.info("curriculum_agent_executing", topic=state.get("topic"))
        
        payload = {
            "topic": state.get("topic"),
            "target_audience": state.get("metadata", {}).get("target_audience", "physicians"),
            "duration_hours": 1,
            "compliance_mode": state.get("compliance_mode", "cme")
        }
        
        result = await self._call_agent("curriculum", "design", payload)
        
        return {
            **state,
            "current_agent": "curriculum",
            "status": "curriculum_designed" if "error" not in result else "curriculum_failed",
            "curriculum": result,
            "errors": state.get("errors", []) + ([result.get("error")] if "error" in result else [])
        }
    
    async def _outcomes_node(self, state: GraphState) -> GraphState:
        """Execute outcomes agent - calls real outcomes service"""
        self.logger.info("outcomes_agent_executing", topic=state.get("topic"))
        
        payload = {
            "topic": state.get("topic"),
            "target_audience": state.get("metadata", {}).get("target_audience", "physicians"),
            "moore_levels": [3, 4, 5],
            "compliance_mode": state.get("compliance_mode", "cme")
        }
        
        result = await self._call_agent("outcomes", "plan", payload)
        
        return {
            **state,
            "current_agent": "outcomes",
            "status": "outcomes_planned" if "error" not in result else "outcomes_failed",
            "outcomes": result,
            "errors": state.get("errors", []) + ([result.get("error")] if "error" in result else [])
        }
    
    async def _qa_compliance_node(self, state: GraphState) -> GraphState:
        """Execute QA/Compliance agent - calls real qa-compliance service"""
        self.logger.info("qa_compliance_executing", 
                        compliance_mode=state.get("compliance_mode"))
        
        payload = {
            "content": state.get("medical_content", ""),
            "compliance_mode": state.get("compliance_mode", "cme"),
            "document_type": state.get("task_type", "general"),
            "references": [],  # QA expects List[Dict], not UUID list - use empty for now
            "checks": ["promotional_language", "fair_balance", "references", "word_count"],
        }
        
        result = await self._call_agent("qa_compliance", "validate", payload)
        
        return {
            **state,
            "current_agent": "qa_compliance",
            "status": "validation_complete" if "error" not in result else "validation_failed",
            "compliance_report": result,
            "errors": state.get("errors", []) + ([result.get("error")] if "error" in result else [])
        }
    
    async def _finalize_node(self, state: GraphState) -> GraphState:
        """Finalize the workflow"""
        self.logger.info("finalizing_workflow", task_id=state.get("task_id"))
        
        return {
            **state,
            "current_agent": "finalize",
            "status": "complete",
            "final_deliverable": {
                "task_id": state.get("task_id"),
                "topic": state.get("topic"),
                "compliance_mode": state.get("compliance_mode"),
                "completed_at": datetime.utcnow().isoformat()
            }
        }
    
    async def run(
        self, 
        task_id: str,
        topic: str,
        task_type: str = "general",
        compliance_mode: str = "auto",
        thread_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the agent graph for a task.
        
        Args:
            task_id: Unique task identifier
            topic: Topic for the task
            task_type: Type of task (needs_assessment, curriculum, etc.)
            compliance_mode: CME mode (cme, non-cme, auto)
            thread_id: Optional thread ID for resuming conversations
            
        Returns:
            Final state with all deliverables
        """
        if not self.compiled_graph:
            await self.initialize()
        
        initial_state: GraphState = {
            "task_id": task_id,
            "topic": topic,
            "compliance_mode": compliance_mode,
            "task_type": task_type,
            "messages": [],
            "research_data": None,
            "medical_content": None,
            "curriculum": None,
            "outcomes": None,
            "compliance_report": None,
            "final_deliverable": None,
            "current_agent": "",
            "status": "started",
            "errors": [],
            "metadata": {
                "started_at": datetime.utcnow().isoformat(),
                "thread_id": thread_id or task_id
            }
        }
        
        config = {"configurable": {"thread_id": thread_id or task_id}}
        
        self.logger.info(
            "langgraph_run_started",
            task_id=task_id,
            task_type=task_type,
            thread_id=thread_id
        )
        
        try:
            final_state = await self.compiled_graph.ainvoke(
                initial_state,
                config=config
            )
            
            self.logger.info(
                "langgraph_run_complete",
                task_id=task_id,
                status=final_state.get("status")
            )
            
            return final_state
            
        except Exception as e:
            self.logger.error("langgraph_run_failed", task_id=task_id, error=str(e))
            return {
                **initial_state,
                "status": "failed",
                "errors": [str(e)]
            }
    
    async def get_thread_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get conversation history for a thread"""
        if not self.checkpointer:
            return []
        
        try:
            states = self.checkpointer.get_state_history(
                {"configurable": {"thread_id": thread_id}}
            )
            return list(states)
        except Exception as e:
            self.logger.error("get_history_failed", thread_id=thread_id, error=str(e))
            return []
    
    async def resume_thread(
        self, 
        thread_id: str, 
        new_message: str
    ) -> Dict[str, Any]:
        """Resume a conversation thread with a new message"""
        if not self.compiled_graph:
            await self.initialize()
        
        config = {"configurable": {"thread_id": thread_id}}
        
        self.logger.info("resuming_thread", thread_id=thread_id)
        
        state_update = {
            "messages": [{"role": "user", "content": new_message}]
        }
        
        final_state = await self.compiled_graph.ainvoke(
            state_update,
            config=config
        )
        
        return final_state


agent_graph: Optional[DHGAgentGraph] = None


async def get_agent_graph() -> DHGAgentGraph:
    """Get or create the agent graph singleton"""
    global agent_graph
    
    if agent_graph is None:
        agent_graph = DHGAgentGraph()
        await agent_graph.initialize()
    
    return agent_graph


async def initialize_langgraph():
    """Initialize LangGraph on startup"""
    global agent_graph
    agent_graph = DHGAgentGraph()
    await agent_graph.initialize()
    logger.info("langgraph_singleton_ready")


async def shutdown_langgraph():
    """Cleanup LangGraph on shutdown"""
    global agent_graph
    if agent_graph and agent_graph.checkpointer:
        logger.info("langgraph_shutdown")
    agent_graph = None
