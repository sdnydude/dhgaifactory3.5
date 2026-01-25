#!/bin/bash
# Complete deployment script for all new features

SERVER="swebber64@10.0.0.251"
PROJECT_DIR="/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5"
SSH_KEY="~/.ssh/id_ed25519_fafstudios"

echo "🚀 DHG AI Factory - Complete Deployment"
echo "========================================"
echo ""

# Step 1: Deploy template renderer
echo "📝 Step 1: Deploying template renderer..."
scp -i $SSH_KEY \
  ~/Desktop/renderer_simple.py \
  $SERVER:$PROJECT_DIR/langgraph_workflows/dhg-cme-research-agent-cloud/src/templates/renderer.py
echo "✅ Template renderer deployed"
echo ""

# Step 2: Add research schemas to registry
echo "📝 Step 2: Adding research request schemas..."
ssh -i $SSH_KEY $SERVER "cat >> $PROJECT_DIR/registry/schemas.py" < ~/Desktop/registry_research_schemas.py
echo "✅ Research schemas added"
echo ""

# Step 3: Restart agent container
echo "🔄 Step 3: Restarting CME Research Agent..."
ssh -i $SSH_KEY $SERVER \
  "cd $PROJECT_DIR/langgraph_workflows/dhg-cme-research-agent-cloud && docker compose restart"
echo "✅ Agent restarted"
echo ""

# Step 4: Test services
echo "🧪 Step 4: Testing services..."
echo ""
echo "Registry API:"
curl -s http://10.0.0.251:8500/api/v1/agents | head -5
echo ""
echo ""
echo "CME Research Agent:"
curl -s http://10.0.0.251:2026/ | head -5
echo ""
echo ""

echo "✅ Deployment complete!"
echo ""
echo "Services:"
echo "  Registry API: http://10.0.0.251:8500"
echo "  CME Agent:    http://10.0.0.251:2026"
