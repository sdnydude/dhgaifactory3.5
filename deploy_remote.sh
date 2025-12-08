#!/bin/bash

# Configuration
REMOTE_HOST="10.0.0.251"
REMOTE_USER="root" # Adjust if necessary, or pass as argument
REMOTE_DIR="/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5" # guessed based on previous context
# User previously mentioned: /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 in PROJECT_SUMMARY.md

echo "🚀 Deploying Web UI to $REMOTE_HOST..."

# 1. Copy Web UI source code and configuration
echo "📦 Copying files..."
rsync -avz --exclude 'node_modules' --exclude 'dist' ./web-ui ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

# 2. Update docker-compose.yml on remote
echo "📄 Updating docker-compose.yml..."
scp ./docker-compose.yml ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/

# 3. Build and Start on Remote
echo "🏗️  Building and Starting Remote Container..."
ssh ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && docker-compose up -d --build web-ui"

echo "✅ Deployment Complete!"
echo "🌍 Access the UI at http://${REMOTE_HOST}:3000"
