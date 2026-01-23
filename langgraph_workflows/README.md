# LangGraph Workflows for LangSmith Cloud

## Files Created

1. **research_workflow.py** - Research workflow using Perplexity
2. **langgraph.json** - Configuration for LangSmith Cloud
3. **requirements.txt** - Python dependencies
4. **deploy.sh** - Deployment script

## Deploy to LangSmith Cloud

### Option 1: Using CLI (Recommended)
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows
./deploy.sh
```

### Option 2: Manual Deployment
```bash
# Install CLI
pip install -U langgraph-cli

# Deploy
langgraph deploy
```

### Option 3: Via LangSmith Studio Web UI
1. Go to https://smith.langchain.com
2. Navigate to your project: dhg-ai-factory
3. Click "Studio" → "Import"
4. Upload `research_workflow.py` and `langgraph.json`

## Test Locally First

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/langgraph_workflows
python -c "
from research_workflow import graph
result = graph.invoke({
    'query': 'GLP-1 receptor agonists and muscle mass',
    'research_results': '',
    'status': 'started'
})
print(result)
"
```

## View in LangSmith Studio

After deployment:
1. Go to https://smith.langchain.com
2. Select project: dhg-ai-factory  
3. Click "Studio" tab
4. See your workflow visually
5. Test with sample inputs
6. View traces and metrics

## Connect to LibreChat

Once deployed, get the cloud URL:
```bash
langgraph deployment list
```

Then update LibreChat to call the cloud endpoint instead of local agents.
