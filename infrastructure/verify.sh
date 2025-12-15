#!/bin/bash

# =============================================================================
# DHG AI Factory - Service Verification Script
# =============================================================================
# Checks health of all services and reports status
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "============================================================================="
echo "DHG AI Factory - Service Health Check"
echo "============================================================================="
echo ""

check_service() {
    local name=$1
    local check_cmd=$2
    
    if eval "$check_cmd" &>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name"
        return 1
    fi
}

check_http() {
    local name=$1
    local url=$2
    
    status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)
    if [[ "$status" =~ ^(200|302|401|403)$ ]]; then
        echo -e "  ${GREEN}✓${NC} $name (HTTP $status)"
        return 0
    else
        echo -e "  ${RED}✗${NC} $name (HTTP $status)"
        return 1
    fi
}

FAILED=0

echo "Docker Services:"
check_service "Docker Daemon" "docker info" || ((FAILED++))
check_service "Docker Compose" "docker compose version" || ((FAILED++))

echo ""
echo "Containers:"
check_service "PostgreSQL" "docker compose exec -T postgres pg_isready -U postgres" || ((FAILED++))
check_service "Onyx API" "docker compose ps onyx-api | grep -q 'running\|Up'" || ((FAILED++))
check_service "Onyx Web" "docker compose ps onyx-web | grep -q 'running\|Up'" || ((FAILED++))
check_service "Onyx Model Server" "docker compose ps onyx-model-server | grep -q 'running\|Up'" || ((FAILED++))
check_service "Ollama" "docker compose ps ollama | grep -q 'running\|Up'" || ((FAILED++))
check_service "Whisper" "docker compose ps whisper | grep -q 'running\|Up'" || ((FAILED++))
check_service "Redis" "docker compose ps redis | grep -q 'running\|Up'" || ((FAILED++))

echo ""
echo "HTTP Endpoints:"
check_http "Onyx Frontend" "http://localhost:3000" || ((FAILED++))
check_http "Onyx API" "http://localhost:8000/health" || ((FAILED++))
check_http "Ollama API" "http://localhost:11434/api/tags" || ((FAILED++))
check_http "Whisper API" "http://localhost:8080" || ((FAILED++))

echo ""
echo "Database:"
if docker compose exec -T postgres psql -U postgres -d onyx -c "SELECT 1" &>/dev/null; then
    TABLES=$(docker compose exec -T postgres psql -U postgres -d onyx -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null | tr -d ' ')
    echo -e "  ${GREEN}✓${NC} PostgreSQL connected ($TABLES tables)"
else
    echo -e "  ${RED}✗${NC} PostgreSQL connection failed"
    ((FAILED++))
fi

echo ""
echo "Ollama Models:"
MODELS=$(curl -s http://localhost:11434/api/tags 2>/dev/null | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | tr '\n' ', ' | sed 's/,$//')
if [ -n "$MODELS" ]; then
    echo -e "  ${GREEN}✓${NC} Available: $MODELS"
else
    echo -e "  ${YELLOW}!${NC} No models downloaded yet"
fi

echo ""
echo "============================================================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All services are healthy!${NC}"
else
    echo -e "${RED}$FAILED service(s) have issues${NC}"
fi
echo "============================================================================="
echo ""

exit $FAILED
