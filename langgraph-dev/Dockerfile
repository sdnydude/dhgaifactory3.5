FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends     curl     git     && rm -rf /var/lib/apt/lists/*

# Install langgraph-cli with inmem support
RUN pip install --no-cache-dir 'langgraph-cli[inmem]' langchain-openai langchain-anthropic

# Create a simple LangGraph project structure
RUN mkdir -p /app/src/agent

# Create the graph.py file
RUN cat > /app/src/agent/__init__.py << 'INITEOF'
INITEOF

RUN cat > /app/src/agent/graph.py << 'GRAPHEOF'
from typing import TypedDict
from langgraph.graph import StateGraph, END

class State(TypedDict):
    messages: list
    response: str

def process_input(state: State) -> State:
    messages = state.get('messages', [])
    last_message = messages[-1] if messages else 'Hello'
    return {
        **state,
        'response': f'Processed: {last_message}'
    }

# Build the graph
builder = StateGraph(State)
builder.add_node('process', process_input)
builder.set_entry_point('process')
builder.add_edge('process', END)

graph = builder.compile()
GRAPHEOF

# Create langgraph.json with CORS configuration
RUN cat > /app/langgraph.json << 'JSONEOF'
{
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "http": {
    "cors": {
      "allow_origins": ["https://smith.langchain.com", "http://localhost:3000", "*"]
    }
  }
}
JSONEOF

# Create pyproject.toml
RUN cat > /app/pyproject.toml << 'TOMLEOF'
[project]
name = "dhg-langgraph"
version = "0.1.0"
description = "DHG AI Factory LangGraph Dev Server"
requires-python = ">=3.11"
dependencies = [
    "langgraph>=0.2.0",
    "langchain-core>=0.2.0",
]
TOMLEOF

# Expose the LangGraph dev server port
EXPOSE 8123

# Default command to run langgraph dev server with tunnel for remote access
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "8123", "--tunnel"]
