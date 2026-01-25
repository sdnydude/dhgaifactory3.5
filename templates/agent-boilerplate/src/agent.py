"""
DHG AI FACTORY - AGENT BOILERPLATE
==================================
Standard template for building LangGraph Cloud agents for DHG.

INSTRUCTIONS:
1. Search and replace "TEMPLATE-AGENT" with your agent name.
2. Define your specific AgentState.
3. Add your nodes and business logic.
4. Update the IO Schema in the manifest.
"""

import os
import json
import httpx
from datetime import datetime
from typing import TypedDict, Annotated, List, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from langgraph.graph import StateGraph, END
from langsmith import traceable
from langchain_core.runnables import RunnableConfig

# =============================================================================
# REGISTRY CLIENT
# =============================================================================

class AIFactoryRegistry:
    def __init__(self, registry_url: Optional[str] = None):
        self.registry_url = registry_url or os.getenv(
            "AI_FACTORY_REGISTRY_URL",
            "http://10.0.0.251:8500"
        )
        self.service_id = "TEMPLATE-AGENT"
        self.version = "1.0.0"

    def get_manifest(self) -> dict:
        return {
            "service": {
                "id": self.service_id,
                "name": "TEMPLATE-AGENT Name",
                "version": self.version,
                "division": "DHG",
                "type": "specialized_agent"
            },
            "capabilities": {"primary": [], "secondary": []},
            "io_schema": {"inputs": {}, "outputs": {}}
        }

    async def register(self):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{self.registry_url}/api/v1/agents/register", json=self.get_manifest())
        except Exception: pass

    async def log_request(self, topic: str, user_id: str, params: dict):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{REGISTRY_URL}/api/v1/research/requests", 
                    json={"user_id": user_id, "agent_type": self.service_id, "input_params": params})
                return resp.json().get("request_id") if resp.status_code == 201 else None
        except Exception: return None

    async def update_request(self, request_id: str, status: str, result: dict = None):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.patch(f"{self.registry_url}/api/v1/research/requests/{request_id}", 
                    json={"status": status, "output_summary": result})
        except Exception: pass

registry = AIFactoryRegistry()

# =============================================================================
# STATE & GRAPH
# =============================================================================

class AgentState(TypedDict):
    topic: str
    request_id: Optional[str]
    user_id: str
    data: Dict[str, Any]
    output: str
    # Add other fields as needed

@traceable(name="log_start")
async def log_start_node(state: AgentState, config: RunnableConfig) -> dict:
    """Entry point node: Initialize tracking and apply config overrides"""
    
    # 1. Get values from config (enables LangGraph Cloud Assistants)
    conf = config.get("configurable", {})
    
    # Example: Override behavior based on configuration
    # output_mode = state.get("mode") or conf.get("mode", "default")
    
    # 2. Log request to Registry
    req_id = await registry.log_request(state["topic"], state.get("user_id", "anonymous"), state)
    
    return {"request_id": req_id}

@traceable(name="process_task")
async def process_node(state: AgentState) -> dict:
    """Core processing logic"""
    # ADD CORE LOGIC HERE
    return {"output": "Completed task."}

@traceable(name="finalize")
async def finalize_node(state: AgentState, config: RunnableConfig) -> dict:
    """Exit point node: Finalize tracking and save results"""
    if state.get("request_id"):
        await registry.update_request(state["request_id"], "completed", {"output_length": len(state["output"])})
    return {}

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("log_start", log_start_node)
    graph.add_node("process", process_node)
    graph.add_node("finalize", finalize_node)
    
    graph.set_entry_point("log_start")
    graph.add_edge("log_start", "process")
    graph.add_edge("process", "finalize")
    graph.add_edge("finalize", END)
    
    return graph.compile()

# Export for LangGraph Cloud
graph = build_graph()
