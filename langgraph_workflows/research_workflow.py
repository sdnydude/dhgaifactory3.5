"""
Research Workflow for LangSmith Cloud
Simple proof-of-concept using Perplexity for research
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
import os


class ResearchState(TypedDict):
    """State for research workflow"""
    query: str
    research_results: str
    status: str


def research_node(state: ResearchState) -> ResearchState:
    """Research using Perplexity API"""
    import httpx
    
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    response = httpx.post(
        "https://api.perplexity.ai/chat/completions",
        headers={"Authorization": f"Bearer {perplexity_key}"},
        json={
            "model": "llama-3.1-sonar-small-128k-online",
            "messages": [
                {"role": "system", "content": "You are a medical research expert."},
                {"role": "user", "content": f"Research: {state['query']}"}
            ]
        },
        timeout=60.0
    )
    
    data = response.json()
    results = data["choices"][0]["message"]["content"]
    
    return {
        **state,
        "research_results": results,
        "status": "complete"
    }


# Create workflow
workflow = StateGraph(ResearchState)
workflow.add_node("research", research_node)
workflow.set_entry_point("research")
workflow.add_edge("research", END)

# Compile
graph = workflow.compile()
