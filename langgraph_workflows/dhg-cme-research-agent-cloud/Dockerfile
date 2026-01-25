FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install LangGraph CLI
RUN pip install --no-cache-dir 'langgraph-cli[inmem]'

# Copy application code
COPY src/ ./src/
COPY schemas/ ./schemas/
COPY langgraph.json .
COPY .env .

# Expose port for LangGraph dev server
EXPOSE 2026

# Start LangGraph dev server
CMD ["langgraph", "dev", "--host", "0.0.0.0", "--port", "2026"]
