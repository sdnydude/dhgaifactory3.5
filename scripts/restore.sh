#!/bin/bash
set -e

# DHG AI Factory - Database Restore Script
# SLO: Restore time < 30 minutes

if [ -z "$1" ]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    echo "Available backups:"
    ls -1 ./backups/dhg_registry_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"
CONTAINER_NAME="dhg-registry-db"
DB_USER="dhg_user"
DB_NAME="dhg_registry"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=========================================="
echo "DHG Registry Database Restore"
echo "=========================================="
echo "Backup file: $BACKUP_FILE"
echo "Target DB: $DB_NAME"
echo ""
echo "WARNING: This will DROP the existing database!"
echo "Press Ctrl+C to cancel, or wait 5 seconds to continue..."
sleep 5

START_TIME=$(date +%s)

echo "Verifying backup integrity..."
if ! gzip -t "$BACKUP_FILE"; then
    echo "ERROR: Backup file is corrupted!"
    exit 1
fi

echo "Stopping dependent services..."
docker-compose stop registry-api asr-service

echo "Dropping existing database..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"

echo "Creating fresh database..."
docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "Restoring backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME"

echo "Verifying restore..."
TABLE_COUNT=$(docker exec "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

if [ "$TABLE_COUNT" -gt 0 ]; then
    echo "Restore verification passed: $TABLE_COUNT tables found"
else
    echo "WARNING: No tables found after restore!"
fi

echo "Restarting services..."
docker-compose start registry-api asr-service

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "=========================================="
echo "Restore complete!"
echo "Duration: ${MINUTES}m ${SECONDS}s"

if [ $DURATION -gt 1800 ]; then
    echo "WARNING: Restore took longer than 30 minutes (SLO violation)"
else
    echo "SLO met: Restore completed in <30 minutes"
fi
echo "=========================================="
