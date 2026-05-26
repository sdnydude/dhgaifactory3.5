---
title: Bulk Ingestion
sidebar_position: 4
---

# Bulk Ingestion

Two Python scripts sync larger content into the DHG Registry on demand. Unlike the 7 capture scripts (which fire in real time during sessions), ingestion scripts are run manually or on a schedule to bulk-load memory files and CLAUDE.md content.

---

## ingest-memory-files

Reads markdown files from a Claude Code memory directory (`~/.claude/projects/<slug>/memory/`), parses their YAML frontmatter, and routes them to the appropriate registry endpoint:

| Frontmatter `type` | Registry target | Method |
|--------------------|----------------|--------|
| `decision` | `POST /api/decision-logs` | Individual POST with duplicate check |
| `feedback`, `reference`, `project`, `user` | `POST /api/doc-pages/bulk` | Batch upsert by `source_file` |

Files named `MEMORY.md` and `decisions_index.md` are skipped (they're index files, not content).

### Usage

```bash
python3 ~/DHG/dhg-memreg/scripts/ingest-memory-files.py \
  --project dhg-ai-factory \
  --memory-dir ~/.claude/projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/memory \
  [--dry-run] \
  [--registry-url http://10.0.0.251:8011]
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--project` | Yes | — | Sets `project_name` in all payloads |
| `--memory-dir` | Yes | — | Directory containing memory `.md` files |
| `--dry-run` | No | `false` | Print what would POST without making network calls |
| `--registry-url` | No | `$REGISTRY_URL` or `http://10.0.0.251:8011` | Override registry URL |

### Docker

```bash
docker run --rm --network=host \
  -v ~/.claude/projects:/projects:ro \
  dhg-memreg ingest-memory-files \
    --project dhg-ai-factory \
    --memory-dir /projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/memory
```

### What Gets Synced

Each memory file with valid frontmatter is parsed and POSTed. Example memory file:

```markdown
---
name: feedback-no-coauthor
description: No co-author trailers on git commits
metadata:
  type: feedback
---

No co-author trailers on commits.
**Why:** Stephen prefers clean commit messages.
**How to apply:** Omit the Co-Authored-By line.
```

This file would be bulk-upserted to `doc_pages` (because `type: feedback` routes to the bulk endpoint). The `source_file` field prevents duplicates on re-runs.

---

## ingest-claude-md

Reads `CLAUDE.md` files from multiple DHG projects, chunks each by markdown heading, and bulk-upserts all chunks to the `doc_pages` table.

### Usage

```bash
python3 ~/DHG/dhg-memreg/scripts/ingest-claude-md.py \
  --dhg-root ~/DHG \
  --projects portage,aifactory \
  --batch-name multi-project \
  [--dry-run] \
  [--registry-url http://10.0.0.251:8011]
```

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--dhg-root` | No | `~/DHG` | Parent directory containing all DHG projects |
| `--projects` | No | All 5 known projects | Comma-separated project keys to process |
| `--batch-name` | No | `multi-project` | Sets the bulk payload's wrapper `project_name` |
| `--dry-run` | No | `false` | Print what would POST without making network calls |
| `--registry-url` | No | `$REGISTRY_URL` or `http://10.0.0.251:8011` | Override registry URL |

### Known Projects

The script maps project keys to directory paths under `--dhg-root`:

| Key | Path | CLAUDE.md location |
|-----|------|--------------------|
| `portage` | `portage/` | `~/DHG/portage/CLAUDE.md` |
| `aifactory` | `aifactory3.5/dhgaifactory3.5/` | `~/DHG/aifactory3.5/dhgaifactory3.5/CLAUDE.md` |
| `c2l-vault` | `c2l-vault/` | `~/DHG/c2l-vault/CLAUDE.md` |
| `claude-code-tresor` | `claude-code-tresor/` | `~/DHG/claude-code-tresor/CLAUDE.md` |
| `digital-harmony-studio` | `Digital-Harmony-Studio-v1/` | `~/DHG/Digital-Harmony-Studio-v1/CLAUDE.md` |

### Docker

```bash
docker run --rm --network=host \
  -v ~/DHG:/dhg:ro \
  dhg-memreg ingest-claude-md \
    --dhg-root /dhg \
    --batch-name multi-project
```

---

## When to Run Ingestion

| Scenario | Command |
|----------|---------|
| After adding/updating memory files | `ingest-memory-files.py` |
| After significant CLAUDE.md changes | `ingest-claude-md.py` |
| First-time setup on a new machine | Both scripts |
| After a major project milestone | Both scripts |

Ingestion is idempotent — running it multiple times on unchanged files produces no duplicates (upsert by `source_file`).
