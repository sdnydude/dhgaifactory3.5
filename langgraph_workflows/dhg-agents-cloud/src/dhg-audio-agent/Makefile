# DHG Audio Analysis Agent — Makefile
# Per Build Spec Section 11

.PHONY: build up down test logs shell pull-model migrate clean

# Build Docker images
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# View logs
logs:
	docker-compose logs -f

# Tail agent logs only
logs-agent:
	docker-compose logs -f audio-agent

# Run tests
test:
	docker-compose exec audio-agent python -m pytest tests/ -v

# Shell into agent container
shell:
	docker-compose exec audio-agent bash

# Pull the LLM model into Ollama
pull-model:
	docker-compose exec ollama ollama pull llama3.1:8b-instruct-q4_K_M

# Run database migrations
migrate:
	docker-compose exec postgres psql -U user -d audio_agent -f /docker-entrypoint-initdb.d/001_initial.sql

# Check health
health:
	curl -s http://localhost:8100/health | jq

# Clean up volumes (WARNING: destroys data)
clean:
	docker-compose down -v

# Development: run locally without Docker
dev:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Quick test: analyze sample audio
test-analyze:
	curl -X POST http://localhost:8100/analyze \
		-H "Content-Type: application/json" \
		-d '{"audio_path": "/data/audio/sample.wav", "diarize": true}'
