#!/bin/bash
set -e

# =============================================================================
# DHG AI Factory - Infrastructure Setup
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/setup.log"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[SETUP]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"; exit 1; }

# Clear log
> "$LOG_FILE"

echo ""
echo "============================================================================="
echo "DHG AI Factory - Infrastructure Setup"
echo "============================================================================="
echo ""

# -----------------------------------------------------------------------------
# Check Docker
# -----------------------------------------------------------------------------
log "Checking Docker..."
if ! command -v docker &> /dev/null; then
    error "Docker not installed. Install from https://docs.docker.com/get-docker/"
fi

if ! docker info &> /dev/null; then
    error "Docker daemon not running. Start Docker Desktop."
fi

if ! docker compose version &> /dev/null; then
    error "Docker Compose not available."
fi

log "Docker OK: $(docker --version)"

# -----------------------------------------------------------------------------
# Check Resources
# -----------------------------------------------------------------------------
log "Checking system resources..."

# Disk space (need ~20GB)
if [[ "$OSTYPE" == "darwin"* ]]; then
    AVAIL_GB=$(df -g / | awk 'NR==2 {print $4}')
else
    AVAIL_GB=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
fi

if [ "$AVAIL_GB" -lt 20 ]; then
    error "Need 20GB disk space. Available: ${AVAIL_GB}GB"
fi
log "Disk: ${AVAIL_GB}GB available"

# Memory
if [[ "$OSTYPE" == "darwin"* ]]; then
    MEM_GB=$(($(sysctl -n hw.memsize) / 1024 / 1024 / 1024))
else
    MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
fi

if [ "$MEM_GB" -lt 8 ]; then
    warn "Low memory: ${MEM_GB}GB (8GB+ recommended)"
else
    log "Memory: ${MEM_GB}GB"
fi

# -----------------------------------------------------------------------------
# Setup Environment
# -----------------------------------------------------------------------------
log "Setting up environment..."

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.template" "$SCRIPT_DIR/.env"
    
    # Generate password
    PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 24)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/POSTGRES_PASSWORD=changeme/POSTGRES_PASSWORD=$PASS/" "$SCRIPT_DIR/.env"
    else
        sed -i "s/POSTGRES_PASSWORD=changeme/POSTGRES_PASSWORD=$PASS/" "$SCRIPT_DIR/.env"
    fi
    log "Created .env with generated password"
else
    log "Using existing .env"
fi

# -----------------------------------------------------------------------------
# Pull Images
# -----------------------------------------------------------------------------
log "Pulling Docker images (this takes a while)..."
cd "$SCRIPT_DIR"
docker compose pull 2>&1 | tee -a "$LOG_FILE"

# -----------------------------------------------------------------------------
# Start Services
# -----------------------------------------------------------------------------
log "Starting services..."
docker compose up -d 2>&1 | tee -a "$LOG_FILE"

# -----------------------------------------------------------------------------
# Wait for Services
# -----------------------------------------------------------------------------
log "Waiting for services to initialize..."
echo "This may take 2-5 minutes on first run..."

wait_for() {
    local name=$1
    local url=$2
    local max=$3
    local i=1
    
    printf "  Waiting for $name"
    while [ $i -le $max ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -qE "200|302|401"; then
            echo -e " ${GREEN}OK${NC}"
            return 0
        fi
        printf "."
        sleep 5
        i=$((i + 1))
    done
    echo -e " ${YELLOW}SLOW${NC}"
    return 1
}

# Wait for key services
sleep 30
wait_for "Vespa" "http://localhost:19071/state/v1/health" 24
wait_for "API Server" "http://localhost:8080/health" 24
wait_for "Web Server" "http://localhost:3000" 12
wait_for "Ollama" "http://localhost:11434/api/tags" 6
wait_for "Whisper" "http://localhost:9090" 6

# -----------------------------------------------------------------------------
# Pull LLM Model
# -----------------------------------------------------------------------------
log "Pulling LLM model..."
docker exec dhg-ollama ollama pull llama3.2 2>&1 | tee -a "$LOG_FILE" || warn "Model pull failed - run manually: docker exec dhg-ollama ollama pull llama3.2"

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------
echo ""
echo "============================================================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "============================================================================="
echo ""
echo "Services:"
echo "  Onyx UI:      http://localhost:3000"
echo "  Onyx API:     http://localhost:8080"
echo "  Ollama:       http://localhost:11434"
echo "  Whisper:      http://localhost:9090"
echo "  PostgreSQL:   localhost:5432"
echo "  Vespa:        localhost:8081"
echo ""
echo "Commands:"
echo "  ./verify.sh           - Check service health"
echo "  ./backup.sh           - Backup data"
echo "  docker compose logs   - View logs"
echo "  docker compose down   - Stop services"
echo ""
echo "Log: $LOG_FILE"
echo "============================================================================="
