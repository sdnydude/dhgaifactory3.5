#!/bin/bash
# Deployment script for DHG AI Factory on 10.0.0.251

echo "=== DHG AI Factory Remote Deployment ==="
echo ""

# Navigate to project directory
cd ~/DHG/aifactory3.5/dhgaifactory3.5 || exit 1

# Pull latest changes
echo "1. Pulling latest changes from GitHub..."
git pull origin master

# Navigate to web-ui directory
cd web-ui || exit 1

# Install dependencies
echo "2. Installing web-ui dependencies..."
npm install

# Build the web-ui (optional, for production)
# echo "3. Building web-ui for production..."
# npm run build

# Navigate back to root
cd ..

# Rebuild and restart Docker containers
echo "3. Rebuilding and restarting Docker containers..."
docker-compose down
docker-compose build
docker-compose up -d

# Check status
echo "4. Checking container status..."
docker-compose ps

echo ""
echo "=== Deployment Complete ==="
echo "Web UI should be accessible at http://10.0.0.251:5173 (dev) or configured port"
echo "Orchestrator WebSocket: ws://10.0.0.251:8011/ws"
