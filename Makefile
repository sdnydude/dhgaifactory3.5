.PHONY: help setup secrets up down restart logs health backup restore rollback clean

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: secrets ## Initial setup - create secrets and directories
	@echo "Creating required directories..."
	@mkdir -p backups data/pgdata secrets test-media
	@echo "Setup complete!"

secrets: ## Generate secret files for Docker
	@echo "Generating secrets..."
	@mkdir -p secrets
	@if [ ! -f secrets/db_password.txt ]; then \
		openssl rand -base64 32 > secrets/db_password.txt; \
		echo "Generated db_password.txt"; \
	fi
	@if [ ! -f secrets/grafana_password.txt ]; then \
		echo "admin" > secrets/grafana_password.txt; \
		echo "Generated grafana_password.txt (default: admin)"; \
	fi
	@chmod 600 secrets/*.txt
	@echo "Secrets created in ./secrets/"

up: ## Start all services
	@echo "Starting DHG AI Factory services..."
	@docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@make health

down: ## Stop all services
	@echo "Stopping DHG AI Factory services..."
	@docker-compose down

restart: down up ## Restart all services

logs: ## Tail logs from all services
	@docker-compose logs -f

health: ## Check health of all services
	@echo "Checking service health..."
	@./scripts/healthcheck.sh

backup: ## Create database backup
	@echo "Creating backup..."
	@./scripts/backup.sh

restore: ## Restore database from backup (usage: make restore BACKUP=filename)
	@if [ -z "$(BACKUP)" ]; then \
		echo "Error: Specify backup file with BACKUP=filename"; \
		echo "Available backups:"; \
		ls -1 backups/; \
		exit 1; \
	fi
	@./scripts/restore.sh backups/$(BACKUP)

rollback: ## One-command rollback - stop and restart all services
	@echo "Rolling back - restarting all services..."
	@docker-compose down
	@docker-compose up -d
	@sleep 5
	@make health
	@echo "Rollback complete!"

clean: down ## Remove all containers, volumes, and data (WARNING: destructive)
	@echo "WARNING: This will remove all data. Press Ctrl+C to cancel, or wait 5 seconds..."
	@sleep 5
	@docker-compose down -v
	@rm -rf data/pgdata
	@echo "Cleanup complete!"

metrics: ## Open Prometheus in browser
	@echo "Opening Prometheus at http://localhost:9090"
	@open http://localhost:9090 || xdg-open http://localhost:9090

dashboard: ## Open Grafana dashboard in browser
	@echo "Opening Grafana at http://localhost:3000"
	@echo "Default credentials: admin/admin"
	@open http://localhost:3000 || xdg-open http://localhost:3000

test-asr: ## Test ASR service with a sample file
	@if [ -z "$(FILE)" ]; then \
		echo "Error: Specify media file with FILE=path/to/file.mp3"; \
		exit 1; \
	fi
	@echo "Transcribing $(FILE)..."
	@curl -X POST -F "file=@$(FILE)" http://localhost:8001/transcribe | jq .

status: ## Show status of all services
	@docker-compose ps
