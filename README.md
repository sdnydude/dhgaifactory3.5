# DHG AI Factory

A local-first, production-ready AI stack designed for high-performance media processing and observability. This system provides a robust foundation for AI workflows, featuring a central registry, GPU-accelerated ASR (Automatic Speech Recognition), and a comprehensive observability suite.

## 🏗 Architecture

The system is composed of three main pillars:

### 1. Registry (Data Layer)
- **Database**: PostgreSQL 15 with `pgvector` extension for vector embeddings.
- **API**: FastAPI service managing media assets, transcripts, and metadata.
- **Schema**: Managed via Alembic migrations.

### 2. ASR Service (Compute Layer)
- **Engine**: OpenAI Whisper (configurable models).
- **Performance**: NVIDIA GPU acceleration support (with CPU fallback).
- **Integration**: Automatically stores results in the Registry.

### 3. Observability (Ops Layer)
- **Metrics**: Prometheus for scraping service metrics (latency, throughput, GPU usage).
- **Visualization**: Grafana for dashboards and alerting.
- **Logs**: Loki for centralized log aggregation.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Make (optional, for convenience commands)
- NVIDIA GPU (Recommended for production)

### Setup & Run

1. **Initialize the environment:**
   ```bash
   make setup
   ```
   This creates necessary directories and generates secure secrets.

2. **Start the stack:**
   ```bash
   make up
   ```

3. **Check health:**
   ```bash
   make health
   ```

## 🖥 Service Endpoints

| Service | URL | Credentials (Default) |
|---------|-----|----------------------|
| **Grafana** | http://localhost:3000 | `admin` / `admin` |
| **Prometheus** | http://localhost:9090 | N/A |
| **Registry API** | http://localhost:8000/docs | N/A |
| **ASR Service** | http://localhost:8001/docs | N/A |

## ⚙️ Configuration

### GPU Support (NVIDIA)
By default, the stack runs in CPU mode for compatibility. To enable GPU support (e.g., for RTX 5080):

1. Copy the example override file:
   ```bash
   cp docker-compose.override.yml.example docker-compose.override.yml
   ```
2. Restart the services:
   ```bash
   make restart
   ```

### Environment Variables
Key configurations can be adjusted in `docker-compose.yml`:
- `WHISPER_MODEL`: Model size (base, small, medium, large-v3).
- `POSTGRES_USER` / `POSTGRES_DB`: Database credentials.

## 🛠 Development

- **Logs**: `make logs` (tail all logs)
- **Backup**: `make backup` (snapshots database)
- **Restore**: `make restore BACKUP=filename`
- **Clean**: `make clean` (WARNING: destroys all data)
