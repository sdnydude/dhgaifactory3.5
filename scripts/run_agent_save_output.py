import os
#!/usr/bin/env python3
"""
Run a LangGraph Cloud agent and save output to markdown file.

Usage:
    python run_agent_save_output.py curriculum_design '{"target_audience": "cardiologists", ...}'
    python run_agent_save_output.py research_protocol '{"target_audience": "cardiologists", ...}'
"""

import sys
import json
import httpx
import asyncio
from pathlib import Path
from datetime import datetime

# LangGraph Cloud config
LANGGRAPH_URL = "https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app"
API_KEY = os.environ.get("LANGGRAPH_API_KEY", "")

OUTPUT_DIR = Path("/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/outputs")

# Map agent name to document field
DOCUMENT_FIELDS = {
    "curriculum_design": "curriculum_document",
    "research_protocol": "protocol_document",
    "marketing_plan": "marketing_document",
    "learning_objectives": "learning_objectives_document",
    "grant_writer": "grant_document",
    "compliance_review": "compliance_report",
}


async def run_agent(agent_name: str, input_data: dict) -> dict:
    """Run agent and return result."""
    
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=300) as client:
        # Create a thread
        response = await client.post(
            f"{LANGGRAPH_URL}/threads",
            headers=headers,
            json={}
        )
        thread = response.json()
        thread_id = thread["thread_id"]
        
        print(f"Created thread: {thread_id}")
        
        # Run the agent
        response = await client.post(
            f"{LANGGRAPH_URL}/threads/{thread_id}/runs",
            headers=headers,
            json={
                "assistant_id": agent_name,
                "input": input_data
            }
        )
        run = response.json()
        run_id = run["run_id"]
        
        print(f"Started run: {run_id}")
        
        # Wait for completion
        while True:
            response = await client.get(
                f"{LANGGRAPH_URL}/threads/{thread_id}/runs/{run_id}",
                headers=headers
            )
            run_status = response.json()
            status = run_status.get("status")
            
            if status == "success":
                break
            elif status in ["error", "failed"]:
                raise Exception(f"Run failed: {run_status}")
            
            print(f"Status: {status}...")
            await asyncio.sleep(2)
        
        # Get final state
        response = await client.get(
            f"{LANGGRAPH_URL}/threads/{thread_id}/state",
            headers=headers
        )
        state = response.json()
        
        return state.get("values", {})


def save_output(agent_name: str, result: dict, input_data: dict):
    """Save agent output to markdown file."""
    
    # Get document field
    doc_field = DOCUMENT_FIELDS.get(agent_name)
    document = result.get(doc_field, "")
    
    if not document:
        print(f"Warning: No document found in field '{doc_field}'")
        # Save full result as JSON instead
        document = f"# Agent Output\n\n```json\n{json.dumps(result, indent=2, default=str)}\n```"
    
    # Create output directory
    agent_dir = OUTPUT_DIR / agent_name
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    disease = input_data.get("disease_state", "unknown").replace(" ", "_").lower()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{disease}_{timestamp}.md"
    filepath = agent_dir / filename
    
    # Write file
    with open(filepath, "w") as f:
        f.write(document)
    
    print(f"\n✅ Saved to: {filepath}")
    return filepath


async def main():
    if len(sys.argv) < 3:
        print("Usage: python run_agent_save_output.py <agent_name> '<json_input>'")
        print("\nAgents: curriculum_design, research_protocol, marketing_plan, learning_objectives, grant_writer, compliance_review")
        sys.exit(1)
    
    agent_name = sys.argv[1]
    input_json = sys.argv[2]
    
    try:
        input_data = json.loads(input_json)
    except json.JSONDecodeError as e:
        print(f"Error parsing input JSON: {e}")
        sys.exit(1)
    
    print(f"Running {agent_name}...")
    print(f"Disease: {input_data.get('disease_state', 'unknown')}")
    print("-" * 50)
    
    result = await run_agent(agent_name, input_data)
    save_output(agent_name, result, input_data)
    
    # Print summary
    tokens = result.get("total_tokens", 0)
    cost = result.get("total_cost", 0)
    print(f"Tokens: {tokens:,} | Cost: ${cost:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
