---
description: Sync Antigravity sessions from Mac to server database
---

# Antigravity Session Sync Workflow

// turbo-all

**Environment:** Mac (export) → Server (ingest)

---

## Overview

Sync Antigravity conversation data from the local app to the CR database.

---

## Step 1: Export from Mac (requires Antigravity running)

On your Mac with Antigravity open:

```bash
cd /path/to/dhgaifactory3.5
python3 scripts/export_antigravity_sessions.py --output sessions.json
```

The script auto-detects:
- Process PID
- CSRF token from process args
- Port via lsof

---

## Step 2: Transfer to Server

```bash
scp sessions.json swebber64@10.0.0.251:/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/swincoming/antigravity_conversations_full.json
```

---

## Step 3: Ingest on Server

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
export DB_PASSWORD="your_password"
python3 scripts/ingest_conversations.py
```

---

## Step 4: Generate Embeddings

```bash
python3 scripts/generate_embeddings.py
```

---

## Step 5: Verify

```bash
psql -h localhost -U dhg -d dhg_registry -c "SELECT COUNT(*) FROM antigravity_messages"
```

---

## Troubleshooting

### Script can't find Antigravity process
- Ensure Antigravity app is running
- Try: `pgrep -f antigravity`

### CSRF token not found
- Check process args: `ps -p <pid> -o args=`
- Look for `--csrf_token` flag

### API calls fail
- Verify port with: `lsof -p <pid> -i -P -n`
- Check if app is responsive
