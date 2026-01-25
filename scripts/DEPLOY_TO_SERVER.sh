#!/bin/bash
# Deploy files to server at 10.0.0.251

SERVER="swebber64@10.0.0.251"
PROJECT_DIR="/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5"

echo "🚀 Deploying to server..."

# 1. Copy template renderer
echo "📝 Copying template renderer..."
scp -i ~/.ssh/id_ed25519_fafstudios \
  ~/Desktop/renderer_simple.py \
  $SERVER:$PROJECT_DIR/langgraph_workflows/dhg-cme-research-agent-cloud/src/templates/renderer.py

# 2. Restart agent container
echo "🔄 Restarting CME Research Agent..."
ssh -i ~/.ssh/id_ed25519_fafstudios $SERVER \
  "cd $PROJECT_DIR/langgraph_workflows/dhg-cme-research-agent-cloud && docker compose restart"

# 3. Test
echo "✅ Testing..."
sleep 5
curl -s http://10.0.0.251:2026/ | head -5

echo ""
echo "✅ Deployment complete!"
echo "Agent running at: http://10.0.0.251:2026"
