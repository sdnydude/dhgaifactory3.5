# SOP: dh40801 Knowledge Base Server Setup

**Date:** 2026-05-19
**Machine:** dh40801 (10.0.0.179)
**Purpose:** Repurpose as DHG Knowledge Base ingestion + retrieval server
**Approach:** Clean and repurpose (NOT fresh install)

## Rationale: Clean vs. Fresh Install

| Factor | Clean & Repurpose | Fresh Install |
|---|---|---|
| Ubuntu 24.04.4 LTS | Already correct | Reinstall same version |
| NVIDIA 570.211 | Working, tested | Reinstall + debug DKMS |
| Docker | Installed, functional | Reinstall |
| SSH + Samba | Configured | Reconfigure |
| Kernel 6.8.0-106 | Stable, 56 days uptime | Risk newer kernel NVIDIA compat |
| Risk | Low — cruft is all Docker | Medium — driver/kernel issues |
| Time | ~1 hour | ~3-4 hours |

**Decision: Clean and repurpose.** The base system is solid. Everything to remove is containerized.

---

## Pre-Flight Checklist

- [ ] Confirm nothing on dh40801 is in active use by anyone
- [ ] Confirm vLLM workload has moved or is no longer needed
- [ ] Back up any files in /home/swebber64 worth keeping (40GB — check what's there)

---

## Phase 1: Clean (30 min)

### 1.1 Stop and remove all Docker workloads

```bash
# Stop running containers
docker stop vllm-server

# Remove all containers
docker rm $(docker ps -aq)

# Remove all images (reclaims ~115GB)
docker rmi $(docker images -q) --force

# Remove volumes (reclaims ~42GB)
docker volume prune -f

# Remove build cache
docker builder prune -af

# Verify clean
docker system df
```

**Expected recovery: ~158GB of disk space**

### 1.2 Remove OpenClaw gateway service

```bash
# Check if it's a systemd service
sudo systemctl list-units | grep -i openclaw
sudo systemctl list-units | grep -i claw

# If found, disable and remove
sudo systemctl stop openclaw-gateway
sudo systemctl disable openclaw-gateway
sudo rm /etc/systemd/system/openclaw-gateway.service
sudo systemctl daemon-reload

# If it's a standalone process
sudo kill $(pgrep -f openclaw)
```

### 1.3 Clean home directory

```bash
# Audit what's in /home/swebber64 (40GB)
du -sh ~/*/  ~/.[^.]*/  2>/dev/null | sort -rh | head -20

# Remove project directories no longer needed (after review)
# DO NOT remove ~/.ssh
```

### 1.4 System update

```bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y
sudo apt autoclean
```

### 1.5 Blacklist kernel + NVIDIA from unattended upgrades

Match g700data1's configuration:

```bash
# /etc/apt/apt.conf.d/50unattended-upgrades
# Add to Unattended-Upgrade::Package-Blacklist:
#   "linux-";
#   "nvidia-";
```

### 1.6 Set swappiness

```bash
echo "vm.swappiness=10" | sudo tee /etc/sysctl.d/99-dhg.conf
sudo sysctl -p /etc/sysctl.d/99-dhg.conf
```

---

## Phase 2: Fleet Integration (20 min)

### 2.1 SSH key setup

```bash
# On dh40801 — add g700data1's keys
# id_ed25519 (already done):
# ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJoRULLEwWK5wBbOOnf/ILwEueECZQ8AZkUgsEOk4t33

# dhg_fleet key (for Ansible):
echo "ssh-ed25519 <g700data1_dhg_fleet_pub_key> swebber64@dhg" >> ~/.ssh/authorized_keys
```

### 2.2 Add to Ansible inventory

Update `ansible/inventory.yml` on g700data1:

```yaml
        dh40801:
          ansible_host: 10.0.0.179
          description: "Knowledge Base server — Docling, WhisperX, Haystack, pgvector"
          cpu: i9_13900kf
          ram_gb: 64
          gpu: rtx_4080
          vram_gb: 16
          os: ubuntu_24_04
          roles: [docker_host, gpu_inference, knowledge_base]
```

Add to groups:

```yaml
    gpu_hosts:
      hosts:
        g700data1:
        dhg5090:
        jason:
        dh40801:

    linux_hosts:
      hosts:
        g700data1:
        dh40801:

    docker_hosts:
      hosts:
        g700data1:
        dh40801:
```

### 2.3 Set hostname consistently

```bash
sudo hostnamectl set-hostname dh40801
```

### 2.4 Add SSH config on g700data1

Create `~/.ssh/config` on g700data1:

```
Host dh40801
    HostName 10.0.0.179
    User swebber64
    IdentityFile ~/.ssh/id_ed25519
```

### 2.5 Add to /etc/hosts on g700data1

```bash
echo "10.0.0.179 dh40801" | sudo tee -a /etc/hosts
```

### 2.6 Run Ansible bootstrap playbook

```bash
cd ~/DHG/aifactory3.5/dhgaifactory3.5/ansible
ansible-playbook playbooks/bootstrap.yml --limit dh40801
ansible-playbook playbooks/security-updates.yml --limit dh40801
ansible-playbook playbooks/nvidia-drivers.yml --limit dh40801  # verify, don't change
```

---

## Phase 3: Knowledge Base Stack Install (45 min)

### 3.1 PostgreSQL + pgvector

```bash
# Option A: Docker (recommended — matches g700data1 pattern)
docker run -d \
  --name dhg-kb-db \
  --restart unless-stopped \
  -e POSTGRES_USER=dhg \
  -e POSTGRES_PASSWORD=<from_vault> \
  -e POSTGRES_DB=dhg_knowledge_base \
  -p 5433:5432 \
  -v dhg-kb-data:/var/lib/postgresql/data \
  pgvector/pgvector:pg15

# Verify
docker exec dhg-kb-db psql -U dhg -d dhg_knowledge_base -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Port 5433 (not 5432) to avoid confusion if g700data1 agents connect directly.

### 3.2 Python environment

```bash
# System Python + venv for the KB pipeline
sudo apt install -y python3.12-venv python3.12-dev ffmpeg

# Create KB venv
python3 -m venv ~/kb-pipeline
source ~/kb-pipeline/bin/activate

# Core packages
pip install docling haystack-ai whisperx
pip install "docling[ocr]"          # EasyOCR backend
pip install haystack-pgvector       # PgvectorDocumentStore
pip install sentence-transformers   # local embeddings (backup to Ollama)
```

### 3.3 Ollama (for nomic-embed-text)

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull nomic-embed-text
```

### 3.4 WhisperX

```bash
# WhisperX needs specific torch + CUDA
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install whisperx

# Test GPU transcription
python -c "import whisperx; print('WhisperX ready')"
```

### 3.5 Docling

```bash
# Pre-download models for offline operation
docling-tools models download

# Test
python -c "from docling.document_converter import DocumentConverter; print('Docling ready')"
```

---

## Phase 4: Verification (15 min)

### 4.1 GPU allocation test

```bash
nvidia-smi  # Should show ~0 MiB used (vLLM removed)
```

### 4.2 Postgres + pgvector test

```bash
docker exec dhg-kb-db psql -U dhg -d dhg_knowledge_base -c "SELECT extversion FROM pg_extension WHERE extname = 'vector';"
```

### 4.3 End-to-end smoke test

```python
# test_pipeline.py — ingest a single PDF, embed, retrieve
from docling.document_converter import DocumentConverter
from haystack_integrations.document_stores.pgvector import PgvectorDocumentStore

converter = DocumentConverter()
result = converter.convert("test.pdf")
print(f"Parsed {len(result.document.texts)} text blocks")
# ... embed and store ...
```

### 4.4 Network connectivity

```bash
# Can reach g700data1
ping -c1 10.0.0.251

# Can reach registry API
curl -s http://10.0.0.251:8011/healthz
```

---

## Phase 5: Observability (Optional, Phase 2)

Wire into g700data1's observability stack:

- Promtail on dh40801 → ship logs to Loki on g700data1
- Node exporter → Prometheus on g700data1 scrapes dh40801:9100
- OTel traces → Tempo on g700data1

This can wait until the KB pipeline is running and proven.

---

## Final Fleet Assignment

| Machine | IP | GPU | Role |
|---|---|---|---|
| g700data1 | 10.0.0.251 | RTX 5080 | Production (agents, registry, frontend, observability) |
| **dh40801** | **10.0.0.179** | **RTX 4080** | **Knowledge Base (Docling, WhisperX, Haystack, pgvector)** |
| dhg5090 | 10.0.0.54 | RTX 5090 | Heavy inference (llama3.3:70b, Nemotron) |
| jason | 10.0.0.80 | RTX 5080 | Secondary inference |
| macbook | 10.0.0.235 | — | Workstation |

---

## Rollback

If anything goes wrong during cleanup, the machine is still functional — we're only removing Docker containers/images and unused software. The base OS, drivers, and network config are untouched.
