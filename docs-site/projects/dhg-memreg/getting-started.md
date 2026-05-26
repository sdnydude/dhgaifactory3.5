---
title: Getting Started
sidebar_position: 1
---

# Getting Started

dhg-memreg is the memory and registry capture toolchain for Digital Harmony Group projects. It gives Claude Code sessions a persistent knowledge base — every decision, insight, bug fix, correction, deferred item, ship session, and test coverage change is automatically captured to the DHG Registry and fed back into future sessions.

The system has three layers:

1. **Capture** — 7 fire-and-forget scripts that POST session events to the registry in real time
2. **Ingestion** — 2 bulk scripts that sync memory files and CLAUDE.md content into the registry
3. **KB Intelligence** — 4 hooks and 1 skill that inject prior knowledge into Claude sessions automatically

## Prerequisites

- **LAN access** to g700data1 (`10.0.0.251:8011`) — the DHG Registry API
- **Python 3.10+** with `httpx` installed
- **jq** and **curl** (used by hooks and capture scripts)
- **Claude Code** installed and configured

## Install

```bash
# 1. Clone the repo
git clone git@github.com:sdnydude/dhg-memreg.git ~/DHG/dhg-memreg

# 2. Symlink capture scripts into Claude Code's scripts directory
bash ~/DHG/dhg-memreg/setup-symlinks.sh

# 3. Verify symlinks
ls -la ~/.claude/scripts/post-*.sh
# All 7 should point to ~/DHG/dhg-memreg/scripts/
```

## Verify End-to-End

Fire a test capture and confirm it reaches the registry:

```bash
~/.claude/scripts/post-insight.sh '{
  "tldr": "memreg install verification",
  "insight_statement": "verifying end-to-end capture pipeline",
  "project_name": "dhg-ai-factory",
  "category": "infra",
  "tags": ["health"],
  "model_name": "manual"
}'
# Expected output: "insight captured: <uuid>"
```

If you see `registry unreachable`, check that `curl http://10.0.0.251:8011/healthz` returns 200.

## Project Structure

```
dhg-memreg/
├── README.md
├── Dockerfile
├── setup-symlinks.sh          # Repoint ~/.claude/scripts/ here
├── scripts/
│   ├── memreg_capture.py      # Unified capture dispatcher
│   ├── ingest-memory-files.py # Bulk memory file sync
│   ├── ingest-claude-md.py    # Bulk CLAUDE.md sync
│   └── post-*.sh              # 7 capture script shims
├── hooks/
│   ├── session-start-kb-briefing.sh
│   ├── user-prompt-kb-inject.sh
│   ├── subagent-start-kb-inject.sh
│   └── pre-tool-kb-search-inject.sh
├── skills/
│   └── kb-search/
│       ├── SKILL.md
│       └── search.sh
├── docker/
│   ├── entrypoint.sh
│   └── requirements.txt
├── tests/
│   ├── test_capture.py
│   ├── test_hooks.py
│   ├── test_ingest_memory_files.py
│   └── test_ingest_claude_md.py
└── .github/workflows/
    └── ci.yml
```

## Docker (Alternative Install)

```bash
docker build -t dhg-memreg:latest ~/DHG/dhg-memreg
docker run --rm --network=host dhg-memreg post-insight '{...}'
```

The `--network=host` flag is required so the container can reach the registry at `10.0.0.251:8011`. The default Docker bridge network does not route to host LAN addresses.

## Next Steps

- [Features](/dhg-memreg/features) — understand what memreg captures and how
- [Capture Scripts](/dhg-memreg/capture-scripts) — the 7 fire-and-forget scripts
- [Hooks](/dhg-memreg/hooks) — how KB intelligence is injected into sessions
- [Architecture](/dhg-memreg/architecture/overview) — data flow and system design
