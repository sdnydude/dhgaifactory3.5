"""
LangSmith MCP Server
====================
Gives Claude direct access to LangSmith Cloud for:
- Querying runs and traces
- Viewing project statistics
- Managing datasets and examples
- Submitting feedback
- Running evaluations

Author: Digital Harmony Group
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from langsmith import Client
from langsmith.schemas import Run, Example, Dataset

# Initialize
server = Server("langsmith-mcp")
client: Optional[Client] = None


def get_client() -> Client:
    """Get or create LangSmith client"""
    global client
    if client is None:
        api_key = os.getenv("LANGCHAIN_API_KEY")
        if not api_key:
            raise ValueError("LANGCHAIN_API_KEY environment variable required")
        client = Client(api_key=api_key)
    return client


# =============================================================================
# TOOLS
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List available LangSmith tools"""
    return [
        Tool(
            name="langsmith_list_projects",
            description="List all projects in LangSmith workspace",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="langsmith_list_runs",
            description="List runs for a project with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name (e.g., 'dhg-cme-research-agent')"
                    },
                    "run_type": {
                        "type": "string",
                        "enum": ["llm", "chain", "retriever", "tool", "agent"],
                        "description": "Filter by run type"
                    },
                    "error": {
                        "type": "boolean",
                        "description": "Filter for runs with errors"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 20,
                        "description": "Max runs to return"
                    },
                    "hours_ago": {
                        "type": "integer",
                        "default": 24,
                        "description": "Filter runs from last N hours"
                    }
                },
                "required": ["project_name"]
            }
        ),
        Tool(
            name="langsmith_get_run",
            description="Get detailed information about a specific run including inputs/outputs",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "The run ID (UUID)"
                    }
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="langsmith_get_run_trace",
            description="Get the full trace tree for a run (parent + all children)",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "The root run ID"
                    }
                },
                "required": ["run_id"]
            }
        ),
        Tool(
            name="langsmith_project_stats",
            description="Get statistics for a project (run counts, latency, costs, errors)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "days": {
                        "type": "integer",
                        "default": 7,
                        "description": "Stats for last N days"
                    }
                },
                "required": ["project_name"]
            }
        ),
        Tool(
            name="langsmith_submit_feedback",
            description="Submit feedback (score, comment) for a run",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "string",
                        "description": "Run ID to give feedback on"
                    },
                    "key": {
                        "type": "string",
                        "default": "quality",
                        "description": "Feedback key (e.g., 'quality', 'accuracy', 'relevance')"
                    },
                    "score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Score between 0 and 1"
                    },
                    "comment": {
                        "type": "string",
                        "description": "Optional feedback comment"
                    }
                },
                "required": ["run_id", "score"]
            }
        ),
        Tool(
            name="langsmith_list_datasets",
            description="List all datasets in the workspace",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "default": 20
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="langsmith_get_dataset",
            description="Get dataset details and examples",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Dataset name"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10,
                        "description": "Max examples to return"
                    }
                },
                "required": ["dataset_name"]
            }
        ),
        Tool(
            name="langsmith_create_dataset",
            description="Create a new dataset for evaluation",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Dataset name"
                    },
                    "description": {
                        "type": "string",
                        "description": "Dataset description"
                    }
                },
                "required": ["name"]
            }
        ),
        Tool(
            name="langsmith_add_example",
            description="Add an example to a dataset",
            inputSchema={
                "type": "object",
                "properties": {
                    "dataset_name": {
                        "type": "string",
                        "description": "Dataset name"
                    },
                    "inputs": {
                        "type": "object",
                        "description": "Example inputs (JSON object)"
                    },
                    "outputs": {
                        "type": "object",
                        "description": "Expected outputs (JSON object)"
                    }
                },
                "required": ["dataset_name", "inputs"]
            }
        ),
        Tool(
            name="langsmith_search_runs",
            description="Search runs by query string (searches inputs, outputs, metadata)",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Project name"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "limit": {
                        "type": "integer",
                        "default": 10
                    }
                },
                "required": ["project_name", "query"]
            }
        ),
        Tool(
            name="langsmith_compare_runs",
            description="Compare two runs side-by-side (inputs, outputs, latency, cost)",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id_1": {
                        "type": "string",
                        "description": "First run ID"
                    },
                    "run_id_2": {
                        "type": "string",
                        "description": "Second run ID"
                    }
                },
                "required": ["run_id_1", "run_id_2"]
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Execute a LangSmith tool"""
    try:
        ls = get_client()
        
        if name == "langsmith_list_projects":
            projects = list(ls.list_projects(limit=50))
            result = [{
                "name": p.name,
                "id": str(p.id),
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "run_count": p.run_count
            } for p in projects]
            
        elif name == "langsmith_list_runs":
            project_name = arguments["project_name"]
            run_type = arguments.get("run_type")
            error = arguments.get("error")
            limit = arguments.get("limit", 20)
            hours_ago = arguments.get("hours_ago", 24)
            
            start_time = datetime.utcnow() - timedelta(hours=hours_ago)
            
            runs = list(ls.list_runs(
                project_name=project_name,
                run_type=run_type,
                error=error,
                start_time=start_time,
                limit=limit
            ))
            
            result = [{
                "id": str(r.id),
                "name": r.name,
                "run_type": r.run_type,
                "status": r.status,
                "error": r.error,
                "latency_ms": int((r.end_time - r.start_time).total_seconds() * 1000) if r.end_time and r.start_time else None,
                "total_tokens": r.total_tokens,
                "total_cost": r.total_cost,
                "start_time": r.start_time.isoformat() if r.start_time else None
            } for r in runs]
            
        elif name == "langsmith_get_run":
            run_id = arguments["run_id"]
            run = ls.read_run(run_id)
            
            result = {
                "id": str(run.id),
                "name": run.name,
                "run_type": run.run_type,
                "status": run.status,
                "inputs": run.inputs,
                "outputs": run.outputs,
                "error": run.error,
                "latency_ms": int((run.end_time - run.start_time).total_seconds() * 1000) if run.end_time and run.start_time else None,
                "total_tokens": run.total_tokens,
                "prompt_tokens": run.prompt_tokens,
                "completion_tokens": run.completion_tokens,
                "total_cost": run.total_cost,
                "feedback_stats": run.feedback_stats,
                "metadata": run.extra.get("metadata") if run.extra else None,
                "tags": run.tags
            }
            
        elif name == "langsmith_get_run_trace":
            run_id = arguments["run_id"]
            
            # Get root run
            root = ls.read_run(run_id)
            
            # Get all child runs
            children = list(ls.list_runs(
                trace_id=run_id,
                limit=100
            ))
            
            def format_run(r):
                return {
                    "id": str(r.id),
                    "name": r.name,
                    "run_type": r.run_type,
                    "parent_run_id": str(r.parent_run_id) if r.parent_run_id else None,
                    "status": r.status,
                    "latency_ms": int((r.end_time - r.start_time).total_seconds() * 1000) if r.end_time and r.start_time else None,
                    "total_tokens": r.total_tokens,
                    "error": r.error[:200] if r.error else None
                }
            
            result = {
                "root": format_run(root),
                "children": [format_run(c) for c in children],
                "total_runs": len(children) + 1
            }
            
        elif name == "langsmith_project_stats":
            project_name = arguments["project_name"]
            days = arguments.get("days", 7)
            
            start_time = datetime.utcnow() - timedelta(days=days)
            
            runs = list(ls.list_runs(
                project_name=project_name,
                start_time=start_time,
                limit=1000
            ))
            
            if runs:
                total_runs = len(runs)
                error_runs = sum(1 for r in runs if r.error)
                total_tokens = sum(r.total_tokens or 0 for r in runs)
                total_cost = sum(r.total_cost or 0 for r in runs)
                latencies = [
                    (r.end_time - r.start_time).total_seconds() * 1000
                    for r in runs if r.end_time and r.start_time
                ]
                
                result = {
                    "project": project_name,
                    "period_days": days,
                    "total_runs": total_runs,
                    "error_runs": error_runs,
                    "error_rate": f"{(error_runs/total_runs)*100:.1f}%",
                    "total_tokens": total_tokens,
                    "total_cost_usd": f"${total_cost:.4f}",
                    "avg_latency_ms": int(sum(latencies)/len(latencies)) if latencies else None,
                    "p95_latency_ms": int(sorted(latencies)[int(len(latencies)*0.95)]) if latencies else None,
                    "run_types": dict(sorted(
                        {rt: sum(1 for r in runs if r.run_type == rt) for rt in set(r.run_type for r in runs)}.items(),
                        key=lambda x: -x[1]
                    ))
                }
            else:
                result = {"message": f"No runs found for {project_name} in last {days} days"}
                
        elif name == "langsmith_submit_feedback":
            run_id = arguments["run_id"]
            key = arguments.get("key", "quality")
            score = arguments["score"]
            comment = arguments.get("comment")
            
            ls.create_feedback(
                run_id=run_id,
                key=key,
                score=score,
                comment=comment
            )
            
            result = {"status": "success", "run_id": run_id, "key": key, "score": score}
            
        elif name == "langsmith_list_datasets":
            limit = arguments.get("limit", 20)
            datasets = list(ls.list_datasets(limit=limit))
            
            result = [{
                "name": d.name,
                "id": str(d.id),
                "description": d.description,
                "example_count": d.example_count,
                "created_at": d.created_at.isoformat() if d.created_at else None
            } for d in datasets]
            
        elif name == "langsmith_get_dataset":
            dataset_name = arguments["dataset_name"]
            limit = arguments.get("limit", 10)
            
            dataset = ls.read_dataset(dataset_name=dataset_name)
            examples = list(ls.list_examples(dataset_name=dataset_name, limit=limit))
            
            result = {
                "name": dataset.name,
                "id": str(dataset.id),
                "description": dataset.description,
                "example_count": dataset.example_count,
                "examples": [{
                    "id": str(e.id),
                    "inputs": e.inputs,
                    "outputs": e.outputs,
                    "created_at": e.created_at.isoformat() if e.created_at else None
                } for e in examples]
            }
            
        elif name == "langsmith_create_dataset":
            name = arguments["name"]
            description = arguments.get("description", "")
            
            dataset = ls.create_dataset(name, description=description)
            
            result = {
                "status": "created",
                "name": dataset.name,
                "id": str(dataset.id)
            }
            
        elif name == "langsmith_add_example":
            dataset_name = arguments["dataset_name"]
            inputs = arguments["inputs"]
            outputs = arguments.get("outputs")
            
            dataset = ls.read_dataset(dataset_name=dataset_name)
            example = ls.create_example(
                inputs=inputs,
                outputs=outputs,
                dataset_id=dataset.id
            )
            
            result = {
                "status": "added",
                "example_id": str(example.id),
                "dataset": dataset_name
            }
            
        elif name == "langsmith_search_runs":
            project_name = arguments["project_name"]
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            
            runs = list(ls.list_runs(
                project_name=project_name,
                filter=f'search("{query}")',
                limit=limit
            ))
            
            result = [{
                "id": str(r.id),
                "name": r.name,
                "run_type": r.run_type,
                "start_time": r.start_time.isoformat() if r.start_time else None,
                "inputs_preview": str(r.inputs)[:200] if r.inputs else None
            } for r in runs]
            
        elif name == "langsmith_compare_runs":
            run_id_1 = arguments["run_id_1"]
            run_id_2 = arguments["run_id_2"]
            
            run1 = ls.read_run(run_id_1)
            run2 = ls.read_run(run_id_2)
            
            def summarize(r):
                return {
                    "id": str(r.id),
                    "name": r.name,
                    "inputs": r.inputs,
                    "outputs": r.outputs,
                    "latency_ms": int((r.end_time - r.start_time).total_seconds() * 1000) if r.end_time and r.start_time else None,
                    "total_tokens": r.total_tokens,
                    "total_cost": r.total_cost,
                    "error": r.error
                }
            
            result = {
                "run_1": summarize(run1),
                "run_2": summarize(run2),
                "comparison": {
                    "latency_diff_ms": (
                        summarize(run1)["latency_ms"] - summarize(run2)["latency_ms"]
                    ) if summarize(run1)["latency_ms"] and summarize(run2)["latency_ms"] else None,
                    "token_diff": (
                        (run1.total_tokens or 0) - (run2.total_tokens or 0)
                    ),
                    "cost_diff": (
                        (run1.total_cost or 0) - (run2.total_cost or 0)
                    )
                }
            }
            
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
        
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


# =============================================================================
# MAIN
# =============================================================================

async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
