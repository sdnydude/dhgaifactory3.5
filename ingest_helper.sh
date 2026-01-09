#!/bin/bash
# Helper script to run Claude data ingestion inside Docker container

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <export-file.zip> [additional-args]"
    echo "Example: $0 ./claude-export.zip --dry-run"
    exit 1
fi

EXPORT_FILE="$1"
shift  # Remove first arg, keep rest

# Copy file to container
echo "Copying $EXPORT_FILE to container..."
docker cp "$EXPORT_FILE" dhg-registry-api:/app/export.zip

# Run ingestion
echo "Running ingestion..."
docker exec dhg-registry-api python3 ingest_claude_data.py \
    --source official_export \
    --input /app/export.zip \
    "$@"

# Cleanup
docker exec dhg-registry-api rm -f /app/export.zip
