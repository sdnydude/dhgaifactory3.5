# DHG CME Research Agent
# Docker container for evidence-based medical research
# Part of DHG AI Factory v3.5 architecture

FROM python:3.11-slim

# Labels for AI Factory integration
LABEL maintainer="Digital Harmony Group <tech@digitalharmonygroup.com>"
LABEL version="1.0.0"
LABEL description="Evidence-based CME research agent with PubMed, Perplexity, and LLM integration"
LABEL ai.factory.type="research-agent"
LABEL ai.factory.domain="medical-education"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

# Create non-root user for security
RUN groupadd -r dhg && useradd -r -g dhg dhguser

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create directories for outputs
RUN mkdir -p /app/outputs /app/cache /app/logs && \
    chown -R dhguser:dhg /app

# Switch to non-root user
USER dhguser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Default command - FastAPI server
CMD ["python", "-m", "uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8080"]
