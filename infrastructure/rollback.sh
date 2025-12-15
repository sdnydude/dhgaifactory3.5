#!/bin/bash

# =============================================================================
# DHG AI Factory - Rollback Script
# =============================================================================
# Quick rollback to the most recent backup
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$SCRIPT_DIR/backups}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[ROLLBACK]${NC} $1"; }
error() { echo -e "${RED}[ROLLBACK]${NC} $1"; exit 1; }

# Find most recent backup
LATEST_BACKUP=$(ls -t "$BACKUP_DIR"/dhg-backup-*.tar.gz 2>/dev/null | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    error "No backups found in $BACKUP_DIR"
fi

log "Most recent backup: $LATEST_BACKUP"
log "Created: $(stat -c %y "$LATEST_BACKUP" 2>/dev/null || stat -f %Sm "$LATEST_BACKUP" 2>/dev/null)"

echo ""
read -p "Rollback to this backup? (y/n) " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    "$SCRIPT_DIR/restore.sh" "$LATEST_BACKUP"
else
    log "Rollback cancelled"
    
    echo ""
    echo "Available backups:"
    ls -lht "$BACKUP_DIR"/dhg-backup-*.tar.gz 2>/dev/null | head -10
fi
