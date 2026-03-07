# Architecture Rules

- LangGraph is the SOLE orchestration platform. Node-RED is fully deprecated.
- LangGraph agents are in langgraph_workflows/dhg-agents-cloud/src/
- Legacy agents in agents/ are being decommissioned — do not build new features on them
- Docker network for main stack: dhgaifactory35_dhg-network (Docker Compose prepends the project directory name)
- All container names must use dhg- prefix
- The web-ui WebSocket connection to port 8011 is BROKEN and will be replaced, not fixed
- AI_FACTORY_REGISTRY_URL should point to http://dhg-registry-api:8000 on dhgaifactory35_dhg-network, NOT port 8500
