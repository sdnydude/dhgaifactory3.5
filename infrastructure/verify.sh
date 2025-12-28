#!/bin/bash

# =============================================================================
# DHG AI Factory - Service Verification
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================================="
echo "DHG AI Factory - Health Check"
echo "============================================================================="
echo ""

FAILED=0

check() {
    local name=$1
    local cmd=$2
    
    if eval "$cmd" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name"
    else
        echo -e "  ${RED}✗${NC} $name"
        ((FAILED++))
    fi
}

http_check() {
    local name=$1
    local url=$2
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [[ "$status" =~ ^(200|302|401|403)$ ]]; then
        echo -e "  ${GREEN}✓${NC} $name (HTTP $status)"
    else
        echo -e "  ${RED}✗${NC} $name (HTTP $status)"
        ((FAILED++))
    fi
}

echo "Docker:"
check "Docker daemon" "docker info"
check "Docker Compose" "docker compose version"

echo ""
echo "Containers:"
check "PostgreSQL" "docker compose exec -T postgres pg_isready -U postgres"
check "Vespa" "docker compose ps vespa | grep -q running"
check "Redis" "docker compose exec -T redis redis-cli ping"
check "Model Server" "docker compose ps model-server | grep -q running"
check "API Server" "docker compose ps api-server | grep -q running"
check "Web Server" "docker compose ps web-server | grep -q running"
check "Ollama" "docker compose ps ollama | grep -q running"
check "Whisper" "docker compose ps whisper | grep -q running"

echo ""
echo "Endpoints:"
http_check "Onyx UI" "http://localhost:3000"
http_check "Onyx API" "http://localhost:8080/health"
http_check "Vespa" "http://localhost:19071/state/v1/health"
http_check "Ollama" "http://localhost:11434/api/tags"
http_check "Whisper" "http://localhost:9090"

echo ""
echo "Ollama Models:"
models=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ' ')
if [ -n "$models" ]; then
    echo -e "  ${GREEN}✓${NC} Models: $models"
else
    echo -e "  ${YELLOW}!${NC} No models (run: docker exec dhg-ollama ollama pull llama3.2)"
fi

echo ""
echo "============================================================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All services healthy${NC}"
else
    echo -e "${RED}$FAILED service(s) have issues${NC}"
fi
echo "============================================================================="
echo ""

exit $FAILED
