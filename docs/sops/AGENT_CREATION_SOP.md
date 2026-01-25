# SOP: DHG AI Agent Creation

**Version:** 1.0.0 (Jan 25, 2026)
**Division:** DHG AI Factory

## 1. Overview
This SOP defines the standardized process for creating AI agents within the DHG AI Factory ecosystem. All agents must follow this structure to ensure interoperability and registry compliance.

## 2. Choosing Agent Type
- **LangGraph Agent**: Use for complex workflows, multi-step research, or stateful interactions. (Preferred for Cloud deployment).
- **FastAPI Docker Agent**: Use for simple tool-based agents or legacy integrations.

## 3. Step-by-Step Walkthrough

### Step 1: Define Agent Manifest
Every agent must have a manifest defining its:
- Identity (id, name, version)
- Capabilities (primary/secondary)
- IO Schema (Pydantic models)
- Models utilized (LLMs)
- External dependencies (APIs)

### Step 2: Implementation (LangGraph)
1. **Define AgentState**: Must include `topic`, `messages`, and tracking fields (`request_id`, `user_id`).
2. **Implement Nodes**: Each function must be `@traceable`.
3. **Build Graph**: Use `StateGraph` and define entry/exit edges.
4. **Compile**: Export strictly as `graph = build_graph()`.

### Step 3: Central Registry Integration
1. Initialize `AIFactoryRegistry` client.
2. Implement `register` call on startup.
3. Implement `heartbeat` loop (every 60s).
4. Implement tracking nodes for database logging (`log_request_node`, `finalize_node`).

### Step 4: Template Rendering
- Use `dhg-style-guide` for outputs.
- Implement a `renderer.py` for multiple formats (JSON, MD, etc.).

## 4. Quality Standards
- No placeholders or stubs in production code.
- Full error handling in every node.
- Real API calls (no dummy data for production).
- LangChain/LangSmith native tracing enabled.

## 5. Deployment
- Push to DHG GitHub Repository.
- Configure `.env` with appropriate API keys (Infisical preferred).
- Register in Central Registry via `http://10.0.0.251:8500`.
