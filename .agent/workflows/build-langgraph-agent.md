---
description: Build new LangGraph agents using proven patterns from successful DHG CME agents
---

# LangGraph Agent Builder Workflow

This workflow creates production-ready LangGraph agents following the patterns established in needs_assessment_agent.py, prose_quality_agent.py, and research_agent.py.

## Pre-Flight Interview

Before starting, gather these details from the user:

### Required Variables

| Variable | Question | Example |
|----------|----------|---------|
| `AGENT_NAME` | What is the agent's name (snake_case)? | `gap_analysis_agent` |
| `AGENT_NUMBER` | What is the agent's number in the 12-agent pipeline? | `3` |
| `AGENT_PURPOSE` | What does this agent do in one sentence? | `Identifies clinical practice gaps from research and clinical data` |
| `SPEC_FILE` | Where is the agent spec? | `DHG-CME-12-Agent-Docs/agents/03-gap-analysis.md` |

### Input/Output Questions

| Variable | Question | Example |
|----------|----------|---------|
| `INPUT_SOURCES` | What agents/sources provide input? | `Research Agent, Clinical Practice Agent` |
| `OUTPUT_FORMAT` | What format does it output? | `JSON structured data + prose document` |
| `OUTPUT_CONSUMERS` | Who consumes this output? | `Needs Assessment Agent, Content Development Agent` |

### Processing Questions

| Variable | Question | Example |
|----------|----------|---------|
| `NEEDS_EXTERNAL_API` | Does it need external APIs (PubMed, Perplexity, etc.)? | `Yes - PubMed for gap validation` |
| `NEEDS_LLM` | Does it need LLM calls? | `Yes - Claude for synthesis` |
| `NUM_SECTIONS` | How many distinct sections/nodes does it need? | `5` |
| `SECTION_NAMES` | What are the section/node names? | `extract_gaps, categorize_gaps, prioritize_gaps, validate_gaps, synthesize_report` |

---

## Step 1: Read and Analyze Spec

// turbo
```bash
cat /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/DHG-CME-12-Agent-Docs/agents/{SPEC_FILE}
```

Extract from spec:
- Role definition
- Input schema
- Output schema
- System prompt
- Quality criteria
- Execution flow

---

## Step 2: Create Agent File Structure

Use this template structure:

```python
"""
{AGENT_NAME} - Agent #{AGENT_NUMBER}
{'=' * (len(AGENT_NAME) + 20)}
{AGENT_PURPOSE}

LangGraph Cloud Ready:
- {OUTPUT_FORMAT}
- Input from: {INPUT_SOURCES}
- Output to: {OUTPUT_CONSUMERS}
"""

import os
import re
import json
import operator
import httpx  # If NEEDS_EXTERNAL_API
from datetime import datetime
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from enum import Enum  # If needed

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langsmith import traceable

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage


# =============================================================================
# CONFIGURATION
# =============================================================================

# Add any enums, constants, or config here


# =============================================================================
# STATE DEFINITION
# =============================================================================

class {AgentName}State(TypedDict):
    # === INPUT ===
    # From upstream agents/intake form
    
    # === PROCESSING ===
    messages: Annotated[list, add_messages]
    
    # Section-specific state
    
    # === OUTPUT ===
    
    # === METADATA ===
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# LLM CLIENT
# =============================================================================

class LLMClient:
    """Claude-based LLM client with cost tracking."""
    
    def __init__(self):
        self.model = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            max_tokens=8192
        )
        self.cost_per_1k_input = 0.003
        self.cost_per_1k_output = 0.015
    
    @traceable(name="{agent_name}_llm_call", run_type="llm")
    async def generate(self, system: str, prompt: str, metadata: dict = None) -> dict:
        """Generate response with cost tracking."""
        messages = [
            SystemMessage(content=system),
            HumanMessage(content=prompt)
        ]
        
        response = await self.model.ainvoke(
            messages,
            config={"metadata": metadata or {}}
        )
        
        input_tokens = 0
        output_tokens = 0
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            input_tokens = response.usage_metadata.get("input_tokens", 0)
            output_tokens = response.usage_metadata.get("output_tokens", 0)
        
        cost = (input_tokens / 1000 * self.cost_per_1k_input) + \
               (output_tokens / 1000 * self.cost_per_1k_output)
        
        return {
            "content": response.content,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost": cost
        }


llm = LLMClient()


# =============================================================================
# EXTERNAL CLIENTS (if needed)
# =============================================================================

# Add PubMedClient, PerplexityClient, etc. if NEEDS_EXTERNAL_API


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

{AGENT_NAME_UPPER}_SYSTEM_PROMPT = """
[Paste from spec or write based on role definition]
"""


# =============================================================================
# BANNED PATTERNS GUIDANCE (if prose output)
# =============================================================================

BANNED_PATTERNS_GUIDANCE = """
=== HIGH PRIORITY FORMATTING RULES ===
NEVER use em dashes (—). Replace with commas or parentheses.
NEVER use colons (:) in prose except for citations.
NEVER start paragraphs with: "Furthermore,", "Moreover,", "Additionally,"
ALWAYS name specific studies - never "Studies show..."

=== BANNED WORDS - USE ALTERNATIVES ===
- "robust" → "strong", "reliable", "effective"
- "paradigm" → "approach", "model", "framework"
- "landscape" (metaphorical) → "environment", "field", "current state"
- "navigate" → "manage", "address", "handle"
- "leverage" → "use", "apply", "employ"
- "holistic" → "comprehensive", "integrated"
- "delve" → "examine", "explore", "investigate"
"""


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="{agent_name}_node_1", run_type="chain")
async def {node_1_name}_node(state: {AgentName}State) -> dict:
    """[Node description]."""
    
    # 1. Extract inputs from state
    
    # 2. Call external APIs if needed
    
    # 3. Build system prompt and user prompt
    system = f"""{SYSTEM_PROMPT}
    
    [Section-specific instructions]
    """
    
    prompt = f"""[Context and instructions]"""
    
    # 4. Generate with LLM
    result = await llm.generate(system, prompt, {"step": "{node_1_name}"})
    
    # 5. Parse response (JSON if structured)
    try:
        content = result["content"]
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {"error": "Failed to parse"}
    except json.JSONDecodeError:
        data = {"error": "Invalid JSON"}
    
    # 6. Update state
    prev_tokens = state.get("total_tokens", 0)
    prev_cost = state.get("total_cost", 0.0)
    
    return {
        "{output_field}": data,
        "total_tokens": prev_tokens + result["total_tokens"],
        "total_cost": prev_cost + result["cost"]
    }


# ... Repeat for each node ...


@traceable(name="{agent_name}_finalize", run_type="chain")
async def finalize_node(state: {AgentName}State) -> dict:
    """Assemble final output."""
    
    # Build final output structure
    output = {
        "metadata": {
            "agent_version": "1.0",
            "execution_timestamp": datetime.now().isoformat(),
            "model_used": "claude-sonnet-4",
            "total_tokens": state.get("total_tokens", 0),
            "total_cost": state.get("total_cost", 0.0)
        },
        # ... assembled sections ...
    }
    
    return {
        "{agent_name}_output": output,
        "messages": [HumanMessage(content="[Summary message]")]
    }


# =============================================================================
# BUILD GRAPH
# =============================================================================

def create_{agent_name}_graph() -> StateGraph:
    """Create the {Agent Name} graph."""
    
    graph = StateGraph({AgentName}State)
    
    # Add nodes
    graph.add_node("{node_1}", {node_1}_node)
    graph.add_node("{node_2}", {node_2}_node)
    # ... add all nodes ...
    graph.add_node("finalize", finalize_node)
    
    # Set entry point
    graph.set_entry_point("{node_1}")
    
    # Add edges (sequential or conditional)
    graph.add_edge("{node_1}", "{node_2}")
    # ... add all edges ...
    graph.add_edge("{last_node}", "finalize")
    graph.add_edge("finalize", END)
    
    return graph


# Compile for LangGraph Cloud
graph = create_{agent_name}_graph().compile()


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        test_state = {
            # Fill in test input
            "messages": [],
            "errors": [],
            "total_tokens": 0,
            "total_cost": 0.0
        }
        
        result = await graph.ainvoke(test_state)
        
        print(f"\n=== {AGENT_NAME} RESULT ===")
        print(f"Total tokens: {result.get('total_tokens', 0)}")
        print(f"Total cost: ${result.get('total_cost', 0):.4f}")
    
    asyncio.run(test())
```

---

## Step 3: Define State Schema

Based on spec inputs/outputs, define the TypedDict:

1. **INPUT section**: Fields from upstream agents
2. **PROCESSING section**: 
   - `messages: Annotated[list, add_messages]` (always required)
   - Section-specific interim data
3. **OUTPUT section**: Final output fields
4. **METADATA section**: `errors`, `model_used`, `total_tokens`, `total_cost`

---

## Step 4: Implement Each Node

For each node from SECTION_NAMES:

1. Add `@traceable` decorator with descriptive name
2. Extract inputs from state
3. Build system + user prompts
4. Call LLM (or external API)
5. Parse response
6. Return state updates with token/cost tracking

**Key patterns:**
- Use `state.get("field", default)` for safe access
- Accumulate tokens: `prev_tokens + result["total_tokens"]`
- Parse JSON safely with try/except

---

## Step 5: Build Graph

1. Instantiate `StateGraph({AgentName}State)`
2. Add all nodes with `graph.add_node()`
3. Set entry point with `graph.set_entry_point()`
4. Add edges (sequential or conditional)
5. End with `graph.add_edge("last_node", END)`
6. Compile: `graph = create_graph().compile()`

---

## Step 6: Register in langgraph.json

// turbo
```bash
cat /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows/dhg-agents-cloud/langgraph.json
```

Add new agent:
```json
{
  "graphs": {
    "existing_agents": "...",
    "{agent_name}": "./src/{agent_name}.py:graph"
  }
}
```

---

## Step 7: Commit and Deploy

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add langgraph_workflows/dhg-agents-cloud/src/{agent_name}.py
git add langgraph_workflows/dhg-agents-cloud/langgraph.json
git commit -m "feat: add {Agent Name} (#{AGENT_NUMBER}) with [description]"
git push origin feature/langgraph-migration
```

---

## Step 8: Test in LangGraph Studio

1. Wait 2-3 min for auto-deploy
2. Open LangGraph Studio
3. Select new agent graph
4. Run with test input
5. Verify:
   - All nodes execute
   - Output matches spec schema
   - Cost/token tracking works
   - No errors in trace

---

## Quality Checklist

Before considering agent complete:

- [ ] State schema matches spec inputs/outputs
- [ ] All nodes have `@traceable` decorators
- [ ] LLM calls track tokens and cost
- [ ] JSON parsing has error handling
- [ ] Graph compiles without errors
- [ ] Registered in langgraph.json
- [ ] Committed with descriptive message
- [ ] Tested in LangGraph Studio
- [ ] Output feeds correctly to downstream agents

---

## Common Patterns Reference

### Accumulating tokens across nodes
```python
prev_tokens = state.get("total_tokens", 0)
return {"total_tokens": prev_tokens + result["total_tokens"]}
```

### Safe JSON extraction
```python
json_match = re.search(r'\{[\s\S]*\}', content)
if json_match:
    data = json.loads(json_match.group())
```

### Prose output with banned patterns
```python
system = f"""{SYSTEM_PROMPT}

{BANNED_PATTERNS_GUIDANCE}

[Section-specific instructions]
"""
```

### Parallel node execution (advanced)
```python
graph.add_edge("start", "node_a")
graph.add_edge("start", "node_b")
graph.add_edge("node_a", "join")
graph.add_edge("node_b", "join")
```
