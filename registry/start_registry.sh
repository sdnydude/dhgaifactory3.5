#!/bin/bash
# Start DHG Registry API with agent and Antigravity endpoints

cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry

# Load environment variables
export $(grep -v "^#" ../.env | xargs)

# Start with uvicorn
uvicorn api:app \
  --host 0.0.0.0 \
  --port 8500 \
  --reload \
  --log-level info
