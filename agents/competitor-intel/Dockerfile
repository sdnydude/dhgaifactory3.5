FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY agents/shared/requirements.txt /tmp/requirements-shared.txt
RUN pip install --no-cache-dir -r /tmp/requirements-shared.txt

COPY agents/competitor-intel/requirements.txt* /tmp/requirements-agent.txt
RUN pip install --no-cache-dir -r /tmp/requirements-agent.txt 2>/dev/null || true

COPY agents/competitor-intel/ /app/
COPY agents/shared/ /app/shared/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
