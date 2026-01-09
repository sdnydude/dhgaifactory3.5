#!/bin/bash

# DHG AI Factory - Quick Start Script
# This script helps you launch the multi-agent CME system

set -e  # Exit on error

echo "🏭 DHG AI Factory - CME Pipeline System"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  No .env file found. Creating from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}✅ Created .env file${NC}"
    echo -e "${YELLOW}📝 Please edit .env and add your API keys:${NC}"
    echo "   - OPENAI_API_KEY or ANTHROPIC_API_KEY"
    echo "   - POSTGRES_PASSWORD"
    echo ""
    echo "Then run this script again."
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker and try again.${NC}"
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install docker-compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Parse command line arguments
ACTION=${1:-up}

case $ACTION in
    build)
        echo "🔨 Building all agents..."
        docker-compose build
        echo -e "${GREEN}✅ Build complete${NC}"
        ;;
        
    up|start)
        echo "🚀 Starting DHG AI Factory..."
        docker-compose up -d
        echo ""
        echo -e "${GREEN}✅ All services started${NC}"
        echo ""
        echo "🔍 Checking service health..."
        sleep 5
        
        # Health check
        HEALTHY=0
        TOTAL=7
        
        for port in 8001 8002 8003 8004 8005 8006 8007; do
            if curl -s http://localhost:$port/health > /dev/null 2>&1; then
                echo -e "${GREEN}✅ Port $port: healthy${NC}"
                ((HEALTHY++))
            else
                echo -e "${YELLOW}⏳ Port $port: starting...${NC}"
            fi
        done
        
        echo ""
        echo "📊 Status: $HEALTHY/$TOTAL agents healthy"
        echo ""
        echo "📚 Access API documentation:"
        echo "   Orchestrator:     http://localhost:8001/docs"
        echo "   Medical LLM:      http://localhost:8002/docs"
        echo "   Research:         http://localhost:8003/docs"
        echo "   Curriculum:       http://localhost:8004/docs"
        echo "   Outcomes:         http://localhost:8005/docs"
        echo "   Competitor Intel: http://localhost:8006/docs"
        echo "   QA/Compliance:    http://localhost:8007/docs"
        echo ""
        echo "🧪 Test the system:"
        echo "   curl http://localhost:8001/health"
        echo ""
        echo "📝 View logs:"
        echo "   docker-compose logs -f"
        ;;
        
    down|stop)
        echo "🛑 Stopping DHG AI Factory..."
        docker-compose down
        echo -e "${GREEN}✅ All services stopped${NC}"
        ;;
        
    restart)
        echo "🔄 Restarting DHG AI Factory..."
        docker-compose down
        docker-compose up -d
        echo -e "${GREEN}✅ System restarted${NC}"
        ;;
        
    logs)
        echo "📋 Showing logs (Ctrl+C to exit)..."
        docker-compose logs -f
        ;;
        
    test)
        echo "🧪 Running system test..."
        echo ""
        echo "Testing orchestrator health..."
        curl -s http://localhost:8001/health | jq . || echo "Orchestrator not responding"
        echo ""
        echo "Testing needs assessment request..."
        curl -X POST http://localhost:8001/orchestrate \
          -H "Content-Type: application/json" \
          -d @test_requests/needs_assessment_diabetes.json \
          | jq .
        ;;
        
    status)
        echo "📊 Service Status:"
        docker-compose ps
        ;;
        
    clean)
        echo "🧹 Cleaning up..."
        docker-compose down -v
        echo -e "${GREEN}✅ Cleanup complete (volumes removed)${NC}"
        ;;
        
    *)
        echo "Usage: ./start.sh [command]"
        echo ""
        echo "Commands:"
        echo "  build    - Build all Docker images"
        echo "  up       - Start all services (default)"
        echo "  down     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show logs"
        echo "  test     - Run system test"
        echo "  status   - Show service status"
        echo "  clean    - Stop services and remove volumes"
        echo ""
        echo "Examples:"
        echo "  ./start.sh build"
        echo "  ./start.sh up"
        echo "  ./start.sh logs"
        ;;
esac
