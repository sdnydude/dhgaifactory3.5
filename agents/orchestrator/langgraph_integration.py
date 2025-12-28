"""
DHG AI FACTORY - LANGGRAPH INTEGRATION
Graph-based agent orchestration with PostgreSQL persistence
"""

import os
import asyncio
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from datetime import datetime
import structlog

from langgraph.graph import StateGraph, END
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    try:
        from langgraph_checkpoint_postgres import PostgresSaver
    except ImportError:
        PostgresSaver = None
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
        
    async def initialize(self):
        """Initialize the graph with PostgreSQL checkpointer"""
        try:
            if self.db_url and PostgresSaver is not None:
                try:
                    self.checkpointer = PostgresSaver.from_conn_string(self.db_url)
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
        workflow.add_node("research", self._research_node)
        workflow.add_node("medical_llm", self._medical_llm_node)
        workflow.add_node("curriculum", self._curriculum_node)
        workflow.add_node("outcomes", self._outcomes_node)
        workflow.add_node("qa_compliance", self._qa_compliance_node)
        workflow.add_node("finalize", self._finalize_node)
        
        workflow.set_entry_point("router")
        
        workflow.add_conditional_edges(
            "router",
            self._determine_next_agent,
            {
                "research": "research",
                "medical_llm": "medical_llm",
                "curriculum": "curriculum",
                "outcomes": "outcomes",
                "qa_compliance": "qa_compliance",
                "finalize": "finalize",
                "end": END
            }
        )
        
        workflow.add_edge("research", "medical_llm")
        workflow.add_edge("medical_llm", "qa_compliance")
        workflow.add_edge("curriculum", "outcomes")
        workflow.add_edge("outcomes", "qa_compliance")
        workflow.add_edge("qa_compliance", "finalize")
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
        """Execute research agent"""
        self.logger.info("research_agent_executing", topic=state.get("topic"))
        
        return {
            **state,
            "current_agent": "research",
            "status": "researching",
            "research_data": {
                "sources": ["pubmed", "cochrane"],
                "references_found": 0,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    
    async def _medical_llm_node(self, state: GraphState) -> GraphState:
        """Execute medical LLM agent"""
        self.logger.info("medical_llm_executing", topic=state.get("topic"))
        
        return {
            **state,
            "current_agent": "medical_llm",
            "status": "generating_content",
            "medical_content": None
        }
    
    async def _curriculum_node(self, state: GraphState) -> GraphState:
        """Execute curriculum agent"""
        self.logger.info("curriculum_agent_executing", topic=state.get("topic"))
        
        return {
            **state,
            "current_agent": "curriculum",
            "status": "designing_curriculum",
            "curriculum": None
        }
    
    async def _outcomes_node(self, state: GraphState) -> GraphState:
        """Execute outcomes agent"""
        self.logger.info("outcomes_agent_executing", topic=state.get("topic"))
        
        return {
            **state,
            "current_agent": "outcomes",
            "status": "planning_outcomes",
            "outcomes": None
        }
    
    async def _qa_compliance_node(self, state: GraphState) -> GraphState:
        """Execute QA/Compliance agent"""
        self.logger.info("qa_compliance_executing", 
                        compliance_mode=state.get("compliance_mode"))
        
        return {
            **state,
            "current_agent": "qa_compliance",
            "status": "validating",
            "compliance_report": {
                "passed": True,
                "violations": [],
                "checked_at": datetime.utcnow().isoformat()
            }
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
