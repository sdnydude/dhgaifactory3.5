#!/bin/bash
set -e

# =============================================================================
# DHG AI Factory - Infrastructure Setup Script
# =============================================================================
# This script sets up the complete AI Factory platform on your local machine.
# Includes: PostgreSQL, Onyx/Danswer (RAG), Ollama (Local LLM), Whisper (Transcription)
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$SCRIPT_DIR/setup.log"
ENV_FILE="$SCRIPT_DIR/.env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"; }
info() { echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"; }

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

check_docker() {
    log "Checking Docker installation..."
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed."
        echo ""
        echo "Please install Docker:"
        echo "  - Mac: https://docs.docker.com/desktop/install/mac-install/"
        echo "  - Windows: https://docs.docker.com/desktop/install/windows-install/"
        echo "  - Linux: https://docs.docker.com/engine/install/"
        echo ""
        read -p "Would you like to attempt automatic installation? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_docker
        else
            exit 1
        fi
    else
        log "Docker is installed: $(docker --version)"
    fi

    if ! docker info &> /dev/null; then
        error "Docker daemon is not running. Please start Docker Desktop."
        exit 1
    fi
    log "Docker daemon is running."
}

check_docker_compose() {
    log "Checking Docker Compose..."
    if ! docker compose version &> /dev/null; then
        if ! docker-compose --version &> /dev/null; then
            error "Docker Compose is not installed."
            exit 1
        fi
    fi
    log "Docker Compose is available."
}

check_ports() {
    log "Checking required ports..."
    PORTS=(5432 3000 8000 8080 11434 9000)
    PORT_NAMES=("PostgreSQL" "Onyx Frontend" "Onyx API" "Whisper" "Ollama" "MinIO")
    
    for i in "${!PORTS[@]}"; do
        PORT=${PORTS[$i]}
        NAME=${PORT_NAMES[$i]}
        if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
            warn "Port $PORT ($NAME) is already in use."
            read -p "Kill the process using port $PORT? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
                log "Killed process on port $PORT"
            else
                error "Cannot proceed with port $PORT in use."
                exit 1
            fi
        fi
    done
    log "All required ports are available."
}

check_disk_space() {
    log "Checking disk space..."
    REQUIRED_GB=20
    if [[ "$OSTYPE" == "darwin"* ]]; then
        AVAILABLE_GB=$(df -g / | awk 'NR==2 {print $4}')
    else
        AVAILABLE_GB=$(df -BG / | awk 'NR==2 {print $4}' | tr -d 'G')
    fi
    
    if [ "$AVAILABLE_GB" -lt "$REQUIRED_GB" ]; then
        error "Insufficient disk space. Required: ${REQUIRED_GB}GB, Available: ${AVAILABLE_GB}GB"
        exit 1
    fi
    log "Disk space OK: ${AVAILABLE_GB}GB available"
}

check_memory() {
    log "Checking system memory..."
    REQUIRED_GB=8
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TOTAL_MEM=$(sysctl -n hw.memsize)
        AVAILABLE_GB=$((TOTAL_MEM / 1024 / 1024 / 1024))
    else
        AVAILABLE_GB=$(free -g | awk '/^Mem:/{print $2}')
    fi
    
    if [ "$AVAILABLE_GB" -lt "$REQUIRED_GB" ]; then
        warn "Low memory: ${AVAILABLE_GB}GB available, ${REQUIRED_GB}GB recommended."
        warn "Some services may run slowly."
    else
        log "Memory OK: ${AVAILABLE_GB}GB available"
    fi
}

install_docker() {
    log "Attempting Docker installation..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        log "Docker installed. Please log out and back in, then run this script again."
        exit 0
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        if command -v brew &> /dev/null; then
            brew install --cask docker
            log "Docker Desktop installed. Please start it from Applications, then run this script again."
            exit 0
        else
            error "Please install Docker Desktop manually from https://docs.docker.com/desktop/install/mac-install/"
            exit 1
        fi
    else
        error "Please install Docker manually for your operating system."
        exit 1
    fi
}

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

setup_env() {
    log "Setting up environment variables..."
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$SCRIPT_DIR/.env.template" ]; then
            cp "$SCRIPT_DIR/.env.template" "$ENV_FILE"
            log "Created .env from template"
        else
            error ".env.template not found"
            exit 1
        fi
    fi
    
    # Generate random passwords if not set
    if grep -q "POSTGRES_PASSWORD=changeme" "$ENV_FILE"; then
        POSTGRES_PASS=$(openssl rand -base64 24 | tr -dc 'a-zA-Z0-9' | head -c 32)
        sed -i.bak "s/POSTGRES_PASSWORD=changeme/POSTGRES_PASSWORD=$POSTGRES_PASS/" "$ENV_FILE"
        log "Generated PostgreSQL password"
    fi
    
    source "$ENV_FILE"
    log "Environment loaded"
}

# =============================================================================
# SERVICE STARTUP
# =============================================================================

start_services() {
    log "Starting Docker services..."
    cd "$SCRIPT_DIR"
    
    # Pull images first
    log "Pulling Docker images (this may take a while)..."
    docker compose pull 2>&1 | tee -a "$LOG_FILE"
    
    # Start services
    log "Starting services..."
    docker compose up -d 2>&1 | tee -a "$LOG_FILE"
    
    log "Waiting for services to be healthy..."
    sleep 10
}

wait_for_service() {
    local name=$1
    local url=$2
    local max_attempts=${3:-30}
    local attempt=1
    
    info "Waiting for $name to be ready..."
    while [ $attempt -le $max_attempts ]; do
        if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|302\|401"; then
            log "$name is ready!"
            return 0
        fi
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    error "$name failed to start after $max_attempts attempts"
    return 1
}

# =============================================================================
# HEALTH CHECKS
# =============================================================================

run_health_checks() {
    log "Running health checks..."
    
    # PostgreSQL
    if docker compose exec -T postgres pg_isready -U postgres &>/dev/null; then
        log "✓ PostgreSQL is healthy"
    else
        error "✗ PostgreSQL is not responding"
        return 1
    fi
    
    # Onyx API
    if wait_for_service "Onyx API" "http://localhost:8000/health" 60; then
        log "✓ Onyx API is healthy"
    else
        warn "✗ Onyx API may still be starting"
    fi
    
    # Onyx Frontend
    if wait_for_service "Onyx Frontend" "http://localhost:3000" 60; then
        log "✓ Onyx Frontend is healthy"
    else
        warn "✗ Onyx Frontend may still be starting"
    fi
    
    # Ollama
    if curl -s http://localhost:11434/api/tags &>/dev/null; then
        log "✓ Ollama is healthy"
    else
        warn "✗ Ollama may still be starting"
    fi
    
    # Whisper
    if wait_for_service "Whisper" "http://localhost:8080/health" 30; then
        log "✓ Whisper is healthy"
    else
        warn "✗ Whisper may still be starting"
    fi
}

# =============================================================================
# POST-SETUP
# =============================================================================

download_models() {
    log "Downloading default LLM models..."
    
    # Pull a default model for Ollama
    info "Pulling llama3.2 model for Ollama (this may take a while)..."
    docker compose exec -T ollama ollama pull llama3.2 2>&1 | tee -a "$LOG_FILE" || warn "Failed to pull llama3.2"
    
    log "Models downloaded"
}

print_summary() {
    echo ""
    echo "============================================================================="
    echo -e "${GREEN}DHG AI Factory - Setup Complete!${NC}"
    echo "============================================================================="
    echo ""
    echo "Services are running at:"
    echo ""
    echo -e "  ${BLUE}Onyx (RAG Platform)${NC}"
    echo "    - Frontend:    http://localhost:3000"
    echo "    - API:         http://localhost:8000"
    echo ""
    echo -e "  ${BLUE}PostgreSQL Database${NC}"
    echo "    - Host:        localhost:5432"
    echo "    - Database:    onyx"
    echo "    - User:        postgres"
    echo ""
    echo -e "  ${BLUE}Ollama (Local LLM)${NC}"
    echo "    - API:         http://localhost:11434"
    echo "    - Model:       llama3.2"
    echo ""
    echo -e "  ${BLUE}Whisper (Transcription)${NC}"
    echo "    - API:         http://localhost:8080"
    echo ""
    echo "============================================================================="
    echo ""
    echo "Next steps:"
    echo "  1. Open Onyx at http://localhost:3000"
    echo "  2. Create an admin account"
    echo "  3. Configure connectors for your documents"
    echo "  4. Connect the Replit frontend to these endpoints"
    echo ""
    echo "Useful commands:"
    echo "  ./verify.sh          - Run health checks"
    echo "  ./backup.sh          - Backup all data"
    echo "  ./restore.sh <file>  - Restore from backup"
    echo "  docker compose logs  - View service logs"
    echo "  docker compose down  - Stop all services"
    echo ""
    echo "Logs saved to: $LOG_FILE"
    echo "============================================================================="
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo "============================================================================="
    echo -e "${BLUE}DHG AI Factory - Infrastructure Setup${NC}"
    echo "============================================================================="
    echo ""
    
    # Clear log file
    > "$LOG_FILE"
    log "Starting setup..."
    
    # Run checks
    check_docker
    check_docker_compose
    check_disk_space
    check_memory
    check_ports
    
    # Setup environment
    setup_env
    
    # Start services
    start_services
    
    # Health checks
    run_health_checks
    
    # Download models
    read -p "Download default LLM models? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        download_models
    fi
    
    # Print summary
    print_summary
}

# Handle errors
trap 'error "Setup failed! Check $LOG_FILE for details."; exit 1' ERR

# Run main
main "$@"
