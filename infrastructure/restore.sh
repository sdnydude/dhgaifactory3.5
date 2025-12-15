#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: ./restore.sh <backup-file.tar.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "$SCRIPT_DIR/backups/"*.tar.gz 2>/dev/null || echo "  No backups found"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: File not found: $BACKUP_FILE"
    exit 1
fi

read -p "This will overwrite existing data. Continue? (y/n) " -n 1 -r
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 0

TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

echo "Extracting backup..."
tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"
BACKUP_DIR=$(ls "$TEMP_DIR")

echo "Stopping services..."
cd "$SCRIPT_DIR"
docker compose down 2>/dev/null || true

echo "Starting PostgreSQL..."
docker compose up -d postgres
sleep 10

echo "Restoring PostgreSQL..."
docker compose exec -T postgres psql -U postgres < "$TEMP_DIR/$BACKUP_DIR/postgres.sql"

echo "Restoring config..."
[ -f "$TEMP_DIR/$BACKUP_DIR/.env" ] && cp "$TEMP_DIR/$BACKUP_DIR/.env" "$SCRIPT_DIR/.env"

echo "Starting all services..."
docker compose up -d

sleep 15
"$SCRIPT_DIR/verify.sh" || echo "Some services may need time to start"

echo "Restore complete!"
