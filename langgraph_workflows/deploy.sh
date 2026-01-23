#!/bin/bash
# Deploy LangGraph workflow to LangSmith Cloud

echo "Deploying Research Workflow to LangSmith Cloud..."

cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows

# Install LangGraph CLI if not installed
pip install -U langgraph-cli

# Deploy to cloud
langgraph deploy \
  --name dhg-research-workflow \
  --description "Medical research workflow using Perplexity" \
  --project dhg-ai-factory

echo "Deployment complete!"
echo "View at: https://smith.langchain.com"
