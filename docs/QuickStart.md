# Quick Start Guide

Get the DHG AI Factory up and running in under 5 minutes.

## Prerequisites

- **Docker Desktop** (running)
- **Make** (optional, but recommended)
- **Git**

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sdnydude/dhgaifactory3.5.git
   cd dhgaifactory3.5
   ```

2. **Run Setup**
   Initialize secrets and directories:
   ```bash
   make setup
   ```

3. **Start the System**
   Launch all services in the background:
   ```bash
   make up
   ```
   *Wait about 30 seconds for the database to initialize.*

4. **Verify Health**
   Ensure everything is running correctly:
   ```bash
   make health
   ```
   You should see `healthy` status for all services.

## Usage

### Accessing Interfaces

- **Grafana (Dashboards)**: [http://localhost:3000](http://localhost:3000) (User: `admin`, Pass: `admin`)
- **Registry API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ASR API Docs**: [http://localhost:8001/docs](http://localhost:8001/docs)

### Transcribing a File

1. Place an audio file (e.g., `test.mp3`) in the project folder.
2. Run the test command:
   ```bash
   make test-asr FILE=test.mp3
   ```
3. View the result in the terminal JSON output.

## Troubleshooting

- **Services failing?** Check logs: `make logs`
- **Database issues?** Reset everything (WARNING: deletes data): `make clean` then `make setup` & `make up`
