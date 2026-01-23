"""DHG Research Agent - Medical research using Perplexity API.

Performs medical research queries and returns structured results.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict
import httpx

from langgraph.graph import StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict


class Context(TypedDict):
    """Context parameters for the research agent.
    
    Optional configuration for research behavior.
    """
    max_results: int  # Maximum number of results to return
    include_citations: bool  # Whether to include citations


@dataclass
class State:
    """Input state for the research agent.
    
    Defines the structure of research requests.
    """
    query: str = ""  # The research query
    results: str = ""  # Research results (output)
    status: str = "pending"  # Status of the research


async def perform_research(state: State, runtime: Runtime[Context]) -> Dict[str, Any]:
    """Perform medical research using Perplexity API.
    
    Uses Perplexity's Sonar model for medical research queries.
    """
    perplexity_key = os.getenv("PERPLEXITY_API_KEY")
    
    if not perplexity_key:
        return {
            "results": "Error: PERPLEXITY_API_KEY not configured",
            "status": "error"
        }
    
    if not state.query:
        return {
            "results": "Error: No query provided",
            "status": "error"
        }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {perplexity_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a medical research expert. Provide comprehensive, evidence-based research summaries with citations."
                        },
                        {
                            "role": "user",
                            "content": state.query
                        }
                    ]
                },
                timeout=60.0
            )
            
            response.raise_for_status()
            data = response.json()
            
            results = data["choices"][0]["message"]["content"]
            citations = data.get("citations", [])
            
            # Format output with citations
            output = f"{results}\n\n"
            if citations:
                output += "Citations:\n"
                for i, citation in enumerate(citations, 1):
                    output += f"{i}. {citation}\n"
            
            return {
                "results": output,
                "status": "complete"
            }
            
    except httpx.HTTPStatusError as e:
        error_detail = ""
        try:
            error_detail = e.response.json()
        except:
            error_detail = e.response.text
        return {
            "results": f"Perplexity API error ({e.response.status_code}): {error_detail}",
            "status": "error"
        }
    except httpx.HTTPError as e:
        return {
            "results": f"HTTP error: {str(e)}",
            "status": "error"
        }
    except Exception as e:
        return {
            "results": f"Unexpected error: {str(e)}",
            "status": "error"
        }


# Define the graph
graph = (
    StateGraph(State, context_schema=Context)
    .add_node(perform_research)
    .add_edge("__start__", "perform_research")
    .compile(name="DHG Research Agent")
)
