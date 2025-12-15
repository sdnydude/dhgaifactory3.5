# DHG AI Factory - Local Infrastructure

Run these scripts on your local machine to set up the full AI Factory stack.

## Quick Start

```bash
cd infrastructure
chmod +x *.sh
./setup.sh
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Onyx UI | 3000 | RAG platform web interface |
| Onyx API | 8080 | RAG backend API |
| Vespa | 8081/19071 | Vector search engine |
| PostgreSQL | 5432 | Database |
| Redis | 6379 | Cache |
| Ollama | 11434 | Local LLM |
| Whisper | 9090 | Transcription |

## Requirements

- Docker 20.10+
- 8GB+ RAM
- 20GB+ disk space
- AVX2 CPU support (for Vespa)

## Scripts

| Script | Description |
|--------|-------------|
| `setup.sh` | Install and start all services |
| `verify.sh` | Check service health |
| `backup.sh` | Backup database and config |
| `restore.sh` | Restore from backup |

## Connect to Replit Frontend

After setup, configure your Replit app's `.env`:

```
ONYX_API_URL=http://YOUR_IP:8080
OLLAMA_URL=http://YOUR_IP:11434
WHISPER_URL=http://YOUR_IP:9090
```

## Troubleshooting

**Vespa "Illegal Instruction"**: CPU lacks AVX2. Use generic image:
```yaml
# In docker-compose.yml, change vespa image to:
image: vespaengine/vespa-generic-intel-x86_64
```

**Out of memory**: Increase Docker Desktop memory (Settings > Resources)

**View logs**: `docker compose logs -f <service-name>`

**Stop everything**: `docker compose down`

**Remove all data**: `docker compose down -v`
