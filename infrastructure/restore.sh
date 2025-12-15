#!/bin/bash

# =============================================================================
# DHG AI Factory - Restore Script
# =============================================================================
# Restores from a backup file
# Usage: ./restore.sh <backup-file.tar.gz>
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[RESTORE]${NC} $1"; }
warn() { echo -e "${YELLOW}[RESTORE]${NC} $1"; }
error() { echo -e "${RED}[RESTORE]${NC} $1"; exit 1; }

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "$SCRIPT_DIR/backups/"*.tar.gz 2>/dev/null || echo "  No backups found in $SCRIPT_DIR/backups/"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    error "Backup file not found: $BACKUP_FILE"
fi

log "Starting restore from: $BACKUP_FILE"

# Confirm
read -p "This will overwrite existing data. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Restore cancelled"
    exit 0
fi

# Create temp directory
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

# Extract backup
log "Extracting backup..."
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_DIR=$(ls "$TEMP_DIR")

# Stop services
log "Stopping services..."
cd "$SCRIPT_DIR"
docker compose down 2>/dev/null || true

# Restore PostgreSQL
if [ -f "$TEMP_DIR/$BACKUP_DIR/postgres.sql" ]; then
    log "Restoring PostgreSQL database..."
    docker compose up -d postgres
    sleep 5
    
    # Wait for PostgreSQL
    for i in {1..30}; do
        if docker compose exec -T postgres pg_isready -U postgres &>/dev/null; then
            break
        fi
        sleep 1
    done
    
    # Drop and recreate database
    docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS onyx" 2>/dev/null || true
    docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE onyx" 2>/dev/null || true
    
    # Restore data
    docker compose exec -T postgres psql -U postgres -d onyx < "$TEMP_DIR/$BACKUP_DIR/postgres.sql"
    log "PostgreSQL restored"
else
    warn "No PostgreSQL backup found"
fi

# Restore configuration
if [ -f "$TEMP_DIR/$BACKUP_DIR/.env" ]; then
    log "Restoring configuration..."
    cp "$TEMP_DIR/$BACKUP_DIR/.env" "$SCRIPT_DIR/.env"
fi

# Restore Onyx data
if [ -f "$TEMP_DIR/$BACKUP_DIR/onyx-data.tar.gz" ]; then
    log "Restoring Onyx data..."
    docker compose up -d onyx-api
    sleep 5
    cat "$TEMP_DIR/$BACKUP_DIR/onyx-data.tar.gz" | docker compose exec -T onyx-api tar xzf - -C / 2>/dev/null || warn "Onyx data restore skipped"
fi

# Start all services
log "Starting all services..."
docker compose up -d

# Wait and verify
sleep 10
log "Verifying services..."
"$SCRIPT_DIR/verify.sh" || warn "Some services may need attention"

log "Restore complete!"
