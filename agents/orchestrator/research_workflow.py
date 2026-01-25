"""
DHG AI FACTORY - Research Workflow (LangGraph)
Simple proof-of-concept to demonstrate LangSmith Studio visualization
"""

import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage
import structlog

logger = structlog.get_logger()


class ResearchState(TypedDict):
    """State for research workflow"""
    query: str
    research_results: str
    formatted_document: str
    status: str


def research_node(state: ResearchState) -> ResearchState:
    """Gather research using Claude"""
    logger.info("research_node_executing", query=state["query"])
    
    # Use Claude to research the topic
    llm = ChatAnthropic(model="claude-3-6-sonnet-20241022", temperature=0.7)
    
    prompt = f"""You are a medical research expert. Research the following topic and provide a comprehensive summary with citations.

Topic: {state["query"]}

Provide:
1. Executive summary
2. Key findings
3. Recent studies (2023-2024)
4. Clinical implications
5. References

Format as markdown."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {
        **state,
        "research_results": response.content,
        "status": "research_complete"
    }


def format_node(state: ResearchState) -> ResearchState:
    """Format research into structured document"""
    logger.info("format_node_executing")
    
    llm = ChatAnthropic(model="claude-3-6-sonnet-20241022", temperature=0.3)
    
    prompt = f"""Format the following research into a professional medical document with proper structure, headings, and citations.

Research Content:
{state["research_results"]}

Create a well-structured document suitable for medical professionals."""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    
    return {
        **state,
        "formatted_document": response.content,
        "status": "complete"
    }


def create_research_workflow():
    """Create and compile the research workflow"""
    
    # Create graph
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("format", format_node)
    
    # Define edges
    workflow.set_entry_point("research")
    workflow.add_edge("research", "format")
    workflow.add_edge("format", END)
    
    # Compile
    app = workflow.compile()
    
    return app


# Test function
async def test_workflow():
    """Test the workflow with a sample query"""
    app = create_research_workflow()
    
    initial_state = {
        "query": "GLP-1 receptor agonists and muscle mass preservation",
        "research_results": "",
        "formatted_document": "",
        "status": "started"
    }
    
    result = await app.ainvoke(initial_state)
    
    print("\\n=== RESEARCH WORKFLOW COMPLETE ===")
    print(f"Status: {result[status]}")
    print(f"\\nFormatted Document:\\n{result[formatted_document][:500]}...")
    
    return result


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_workflow())
