# Warp Terminal Workflows

This document outlines recommended workflows for interacting with the DHG AI Factory using [Warp Terminal](https://www.warp.dev/). You can save these as personal or team workflows for quick access.

## 🚀 Service Control

| Workflow Name | Command | Description |
|--------------|---------|-------------|
| **Start AI Factory** | `make up` | Starts all services in detached mode and waits for health checks. |
| **Stop AI Factory** | `make down` | Stops all running services. |
| **Restart Services** | `make restart` | Full restart of the stack. |
| **Follow Logs** | `make logs` | Tails logs from all containers. |

## 🔍 Observability & Health

| Workflow Name | Command | Description |
|--------------|---------|-------------|
| **Check Health** | `make health` | Runs the healthcheck script against all endpoints. |
| **Open Grafana** | `make dashboard` | Opens the Grafana dashboard in your default browser. |
| **Open Prometheus** | `make metrics` | Opens the Prometheus UI in your default browser. |
| **Service Status** | `make status` | Shows the current status of docker containers. |

## 💾 Data Management

| Workflow Name | Command | Description |
|--------------|---------|-------------|
| **Backup Database** | `make backup` | Creates a timestamped backup of the Registry database. |
| **Restore Database** | `make restore BACKUP={{backup_file}}` | Restores the database from a specific backup file. |
| **Clean Environment** | `make clean` | **WARNING**: Destroys all containers and data volumes. |

## 🧪 Testing

| Workflow Name | Command | Description |
|--------------|---------|-------------|
| **Test ASR** | `make test-asr FILE={{path_to_audio}}` | Sends an audio file to the ASR service for transcription. |
