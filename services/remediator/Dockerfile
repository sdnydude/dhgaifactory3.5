FROM python:3.11-slim

# Docker CLI for the allowlisted read-only diagnostics (docker inspect / ps /
# logs --tail / stats --no-stream); curl for the http://dhg-* queries.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        gnupg && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" \
        > /etc/apt/sources.list.d/docker.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY allowlist.py remediator.py ./

# Non-root. Socket access comes from `group_add` (host docker gid) in
# docker-compose.yml, not from running as root.
RUN useradd --create-home --uid 10001 remediator
USER remediator

CMD ["python", "-u", "remediator.py"]
