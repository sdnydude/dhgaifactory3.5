FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy shared requirements
COPY agents/shared/requirements.txt /tmp/requirements-shared.txt
RUN pip install --no-cache-dir -r /tmp/requirements-shared.txt

# Copy agent-specific requirements if they exist
COPY agents/orchestrator/requirements.txt* /tmp/requirements-agent.txt
RUN pip install --no-cache-dir -r /tmp/requirements-agent.txt || true

# Copy application code
COPY agents/orchestrator/ /app/
COPY agents/shared/ /app/shared/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
