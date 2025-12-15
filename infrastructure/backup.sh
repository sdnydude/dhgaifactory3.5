#!/bin/bash

# =============================================================================
# DHG AI Factory - Backup Script
# =============================================================================
# Creates a timestamped backup of all data (database, volumes, config)
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env" 2>/dev/null || true

BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="dhg-backup-$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[BACKUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[BACKUP]${NC} $1"; }
error() { echo -e "${RED}[BACKUP]${NC} $1"; exit 1; }

# Create backup directory
mkdir -p "$BACKUP_PATH"

log "Starting backup: $BACKUP_NAME"

# Backup PostgreSQL
log "Backing up PostgreSQL database..."
docker compose exec -T postgres pg_dump -U postgres -d onyx > "$BACKUP_PATH/postgres.sql" || error "PostgreSQL backup failed"
log "PostgreSQL backup complete"

# Backup environment
log "Backing up configuration..."
cp "$SCRIPT_DIR/.env" "$BACKUP_PATH/.env" 2>/dev/null || true
cp "$SCRIPT_DIR/docker-compose.yml" "$BACKUP_PATH/docker-compose.yml"

# Backup Ollama models list
log "Recording Ollama models..."
curl -s http://localhost:11434/api/tags > "$BACKUP_PATH/ollama-models.json" 2>/dev/null || true

# Backup Onyx data (if accessible)
log "Backing up Onyx data..."
docker compose exec -T onyx-api tar czf - /home/storage 2>/dev/null > "$BACKUP_PATH/onyx-data.tar.gz" || warn "Onyx data backup skipped"

# Create metadata
cat > "$BACKUP_PATH/metadata.json" << EOF
{
    "timestamp": "$TIMESTAMP",
    "backup_name": "$BACKUP_NAME",
    "created_at": "$(date -Iseconds)",
    "hostname": "$(hostname)",
    "docker_version": "$(docker --version)",
    "services": $(docker compose ps --format json 2>/dev/null || echo "[]")
}
EOF

# Compress backup
log "Compressing backup..."
cd "$BACKUP_DIR"
tar czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

BACKUP_SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
log "Backup complete: $BACKUP_DIR/$BACKUP_NAME.tar.gz ($BACKUP_SIZE)"

# Cleanup old backups
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
log "Cleaning up backups older than $RETENTION_DAYS days..."
find "$BACKUP_DIR" -name "dhg-backup-*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

log "Backup finished successfully!"
