#!/bin/bash

# Configuration
REMOTE_HOST="10.0.0.251"
REMOTE_USER="swebber64"
REMOTE_DIR="/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5"
# User previously mentioned: /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 in PROJECT_SUMMARY.md

echo "🚀 Deploying Web UI to $REMOTE_HOST..."

# 1. Copy Web UI and Agents source code
echo "📦 Copying files..."
rsync -avz -e "ssh -i ~/.ssh/id_ed25519_fafstudios" --exclude 'node_modules' --exclude 'dist' ./web-ui ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/
rsync -avz -e "ssh -i ~/.ssh/id_ed25519_fafstudios" --exclude '__pycache__' ./agents ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

# 2. Update docker-compose.yml on remote
echo "📄 Updating docker-compose.yml..."
scp -i ~/.ssh/id_ed25519_fafstudios ./docker-compose.yml ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

# 3. Build and Start on Remote
echo "🏗️  Building and Starting Remote Containers..."
ssh -i ~/.ssh/id_ed25519_fafstudios ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && docker-compose up -d --build web-ui orchestrator"

echo "✅ Deployment Complete!"
echo "🌍 Access the UI at http://${REMOTE_HOST}:3005"
