# User Manual

Welcome to the DHG AI Factory. This manual covers detailed operations, configuration, and maintenance of the system.

## Table of Contents
1. [System Configuration](#system-configuration)
2. [Operational Workflows](#operational-workflows)
3. [Maintenance & Backups](#maintenance--backups)
4. [API Reference](#api-reference)

---

## System Configuration

### Environment Variables
The system uses `docker-compose.yml` for configuration. Key variables include:

- **Registry Service**:
  - `POSTGRES_USER`: Database username (default: `dhg_user`)
  - `POSTGRES_DB`: Database name (default: `dhg_registry`)

- **ASR Service**:
  - `WHISPER_MODEL`: Model size to load. Options: `tiny`, `base`, `small`, `medium`, `large-v3`. Larger models require more VRAM.
  - `CUDA_VISIBLE_DEVICES`: GPU index to use (default: `0`).

### GPU Acceleration
To enable NVIDIA GPU support (e.g., for RTX 5080):
1. Ensure NVIDIA Container Toolkit is installed on your host.
2. Create an override file:
   ```bash
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```
3. Restart services: `make restart`

---

## Operational Workflows

### 1. Transcribing Audio
You can transcribe audio via the API or CLI.

**Via CLI (Make):**
```bash
make test-asr FILE=path/to/audio.mp3
```

**Via API (Curl):**
```bash
curl -X POST -F "file=@/path/to/audio.mp3" http://localhost:8001/transcribe
```

### 2. Monitoring Performance
Open Grafana at [http://localhost:3000](http://localhost:3000).
- **Login**: `admin` / `admin` (change this on first login!)
- **Dashboards**: Navigate to "Dashboards" > "DHG Core Golden" to view:
  - Real-time ASR latency
  - Request throughput
  - System resource usage

---

## Maintenance & Backups

### Database Backups
The system includes a script to backup the PostgreSQL registry.
```bash
make backup
```
Backups are stored in the `backups/` directory with a timestamp.

### Restoring Data
To restore from a backup:
1. List available backups: `ls -l backups/`
2. Run restore command:
   ```bash
   make restore BACKUP=backup_2025_11_28_120000.sql.gz
   ```

### Logs
Logs are aggregated in Loki but can be viewed directly via Docker:
- **All services**: `make logs`
- **Specific service**: `docker-compose logs -f asr-service`

---

## API Reference

### Registry API (Port 8000)
- `GET /healthz`: Service health status.
- `GET /metrics`: Prometheus metrics.
- `POST /api/v1/transcriptions`: Store a new transcription result.

### ASR API (Port 8001)
- `GET /healthz`: Service health and model status.
- `POST /transcribe`: Upload and transcribe an audio file.
