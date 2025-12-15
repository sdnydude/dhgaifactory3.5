#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_DIR="$SCRIPT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="dhg-backup-$TIMESTAMP"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

mkdir -p "$BACKUP_PATH"

echo "Creating backup: $BACKUP_NAME"

# PostgreSQL
echo "  Backing up PostgreSQL..."
docker compose exec -T postgres pg_dumpall -U postgres > "$BACKUP_PATH/postgres.sql"

# Config
echo "  Backing up config..."
cp "$SCRIPT_DIR/.env" "$BACKUP_PATH/.env" 2>/dev/null || true
cp "$SCRIPT_DIR/docker-compose.yml" "$BACKUP_PATH/"

# Ollama models list
echo "  Recording Ollama models..."
curl -s http://localhost:11434/api/tags > "$BACKUP_PATH/ollama-models.json" 2>/dev/null || true

# Compress
echo "  Compressing..."
cd "$BACKUP_DIR"
tar czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
rm -rf "$BACKUP_NAME"

SIZE=$(du -h "$BACKUP_DIR/$BACKUP_NAME.tar.gz" | cut -f1)
echo "Backup complete: $BACKUP_DIR/$BACKUP_NAME.tar.gz ($SIZE)"

# Cleanup old backups (30 days)
find "$BACKUP_DIR" -name "dhg-backup-*.tar.gz" -mtime +30 -delete 2>/dev/null || true
