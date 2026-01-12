FROM python:3.11-slim

WORKDIR /app

# Install base dependencies including exempi for XMP metadata
RUN apt-get update && apt-get install -y curl libexempi-dev && rm -rf /var/lib/apt/lists/*

# Copy Core Library first (to leverage caching if we had separate requirements)
COPY agents/shared/ /app/shared/

# Install dependencies (FastAPI, Uvicorn, etc.)
COPY agents/shared/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install module to allow importing 'dhg_core'
ENV PYTHONPATH=/app/shared

# Copy Agent Code
COPY agents/visuals/ /app/agents/visuals/

# Install visuals-specific dependencies (google-generativeai, pillow)
RUN pip install --no-cache-dir -r /app/agents/visuals/requirements.txt

# Expose Port
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run
CMD ["uvicorn", "agents.visuals.main:app", "--host", "0.0.0.0", "--port", "8000"]
