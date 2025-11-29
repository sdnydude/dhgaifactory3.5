FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install Python and system dependencies for faster-whisper
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the application
ENTRYPOINT ["./entrypoint.sh"]
