#!/bin/bash
set -e

# DHG AI Factory - Comprehensive Health Check Script
# Verifies: service health, Prometheus targets, alerts, and metrics endpoints

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "DHG AI Factory - Health Check"
echo "=========================================="
echo ""

FAILED=0

# Function to check HTTP endpoint
check_endpoint() {
    local name=$1
    local url=$2
    local expected_code=${3:-200}
    
    if curl -sf -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_code"; then
        echo -e "${GREEN}✓${NC} $name: OK"
        return 0
    else
        echo -e "${RED}✗${NC} $name: FAILED"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Check service health endpoints
echo "Checking Service Health Endpoints..."
echo "--------------------------------------"
check_endpoint "Registry API" "http://localhost:8000/healthz"
check_endpoint "ASR Service" "http://localhost:8001/healthz"
check_endpoint "Prometheus" "http://localhost:9090/-/healthy"
check_endpoint "Grafana" "http://localhost:3000/api/health"
check_endpoint "Loki" "http://localhost:3100/ready"
echo ""

# Check metrics endpoints
echo "Checking Metrics Endpoints..."
echo "--------------------------------------"
check_endpoint "Registry Metrics" "http://localhost:8000/metrics"
check_endpoint "ASR Metrics" "http://localhost:8001/metrics"
echo ""

# Check Prometheus targets
echo "Checking Prometheus Targets..."
echo "--------------------------------------"
TARGETS_DOWN=$(curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | select(.health != "up") | .scrapeUrl' 2>/dev/null)

if [ -z "$TARGETS_DOWN" ]; then
    echo -e "${GREEN}✓${NC} All Prometheus targets are up"
else
    echo -e "${RED}✗${NC} Some Prometheus targets are down:"
    echo "$TARGETS_DOWN"
    FAILED=$((FAILED + 1))
fi
echo ""

# Check for firing alerts
echo "Checking Prometheus Alerts..."
echo "--------------------------------------"
FIRING_ALERTS=$(curl -s http://localhost:9090/api/v1/alerts | jq -r '.data.alerts[] | select(.state == "firing") | .labels.alertname' 2>/dev/null)

if [ -z "$FIRING_ALERTS" ]; then
    echo -e "${GREEN}✓${NC} No alerts firing"
else
    echo -e "${RED}✗${NC} Alerts currently firing:"
    echo "$FIRING_ALERTS"
    FAILED=$((FAILED + 1))
fi
echo ""

# Check database connectivity
echo "Checking Database..."
echo "--------------------------------------"
if docker exec dhg-registry-db pg_isready -U dhg_user -d dhg_registry > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Database is ready"
else
    echo -e "${RED}✗${NC} Database is not ready"
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
echo "=========================================="
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All health checks passed!${NC}"
    exit 0
else
    echo -e "${RED}Health check failed with $FAILED errors${NC}"
    exit 1
fi
