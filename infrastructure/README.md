# DHG AI Factory - Infrastructure Setup

This directory contains everything needed to set up the DHG AI Factory platform on your local machine or server.

## Quick Start

```bash
# 1. Make scripts executable
chmod +x *.sh

# 2. Copy and configure environment
cp .env.template .env
# Edit .env with your settings

# 3. Run setup
./setup.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DHG AI Factory                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │
│  │   Onyx      │  │   Ollama    │  │   Whisper   │          │
│  │   (RAG)     │  │ (Local LLM) │  │(Transcribe) │          │
│  │  :3000/:8000│  │   :11434    │  │    :8080    │          │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘          │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          │                                   │
│                  ┌───────┴───────┐                          │
│                  │  PostgreSQL   │                          │
│                  │    :5432      │                          │
│                  └───────────────┘                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Services

| Service | Port | Description |
|---------|------|-------------|
| Onyx Frontend | 3000 | RAG platform UI |
| Onyx API | 8000 | RAG backend API |
| PostgreSQL | 5432 | Central database |
| Ollama | 11434 | Local LLM server |
| Whisper | 8080 | Transcription API |
| Redis | 6379 | Caching (optional) |

## Scripts

| Script | Description |
|--------|-------------|
| `setup.sh` | Initial setup - installs and configures all services |
| `verify.sh` | Health check - verifies all services are running |
| `backup.sh` | Creates timestamped backup of all data |
| `restore.sh` | Restores from a backup file |
| `rollback.sh` | Quick rollback to most recent backup |

## Configuration

Edit `.env` to customize:

```bash
# Database
POSTGRES_PASSWORD=your-secure-password

# Whisper model size (tiny/base/small/medium/large)
WHISPER_MODEL=base

# Cloud API fallbacks (optional)
GEMINI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
```

## Requirements

- **Docker**: 20.10+
- **Docker Compose**: v2+
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 20GB minimum
- **GPU**: Optional, improves LLM/transcription speed

## Connecting to Replit Frontend

After setup, configure your Replit app with these endpoints:

```javascript
// In your Replit frontend config
const API_ENDPOINTS = {
  onyx: 'http://YOUR-IP:8000',
  ollama: 'http://YOUR-IP:11434',
  whisper: 'http://YOUR-IP:8080',
};
```

Replace `YOUR-IP` with your machine's IP address or hostname.

## Troubleshooting

### Services won't start
```bash
# Check logs
docker compose logs

# Restart specific service
docker compose restart onyx-api
```

### Port conflicts
```bash
# Find process using port
lsof -i :3000

# Kill it
kill -9 <PID>
```

### Out of memory
```bash
# Reduce Whisper model size in .env
WHISPER_MODEL=tiny
```

### GPU not detected (Ollama)
```bash
# Remove GPU config from docker-compose.yml
# Or install NVIDIA Container Toolkit:
# https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
```

## Maintenance

### Update services
```bash
docker compose pull
docker compose up -d
```

### View logs
```bash
docker compose logs -f
```

### Clean up
```bash
# Stop and remove containers
docker compose down

# Remove all data (CAUTION)
docker compose down -v
```

## Support

- Logs: `setup.log`
- Backups: `./backups/`
- GitHub: https://github.com/sdnydude/dhgaifactory3.5
