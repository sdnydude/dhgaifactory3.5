#!/bin/bash
set -e

echo "Starting ASR Service..."
echo "Whisper Model: ${WHISPER_MODEL:-base}"
echo "Registry API: ${REGISTRY_API_URL:-http://registry-api:8000}"

# Start the FastAPI application
exec uvicorn api:app --host 0.0.0.0 --port 8000 --log-level info
