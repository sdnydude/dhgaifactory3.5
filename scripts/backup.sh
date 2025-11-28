#!/bin/bash
set -e

# DHG AI Factory - Database Backup Script
# Creates compressed PostgreSQL backups with timestamp
# SLO: Restore time < 30 minutes

BACKUP_DIR="./backups"
TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
BACKUP_FILE="$BACKUP_DIR/dhg_registry_$TIMESTAMP.sql.gz"
CONTAINER_NAME="dhg-registry-db"
DB_USER="dhg_user"
DB_NAME="dhg_registry"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting DHG Registry backup..."
echo "Timestamp: $TIMESTAMP"

# Create backup using pg_dump
docker exec "$CONTAINER_NAME" pg_dump -U "$DB_USER" -d "$DB_NAME" --format=plain --compress=0 | gzip > "$BACKUP_FILE"

# Verify backup was created
if [ -f "$BACKUP_FILE" ]; then
    SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
    echo "Backup created successfully: $BACKUP_FILE"
    echo "Size: $SIZE"
    
    # Verify backup integrity
    if gzip -t "$BACKUP_FILE" 2>/dev/null; then
        echo "Backup integrity verified (gzip test passed)"
    else
        echo "WARNING: Backup integrity check failed!"
        exit 1
    fi
else
    echo "ERROR: Backup file was not created"
    exit 1
fi

# Cleanup old backups (keep last 30 days)
echo "Cleaning up old backups (keeping last 30 days)..."
find "$BACKUP_DIR" -name "dhg_registry_*.sql.gz" -type f -mtime +30 -delete
REMAINING=$(ls -1 "$BACKUP_DIR"/dhg_registry_*.sql.gz 2>/dev/null | wc -l)
echo "Total backups retained: $REMAINING"

echo "Backup complete!"
