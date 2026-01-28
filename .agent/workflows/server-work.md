---
description: All DHG AI Factory work must be done on .251 server (Remote-SSH setup)
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Server-First Development Workflow (Remote-SSH)

// turbo-all

## Current Environment

**VS Code Remote-SSH** is connected directly to **10.0.0.251 (g700data1)**.

This means:
- ✅ All file tools work directly on the server
- ✅ No SSH wrapping required
- ✅ `write_to_file`, `replace_file_content`, etc. operate natively on server paths
- ✅ Commands run directly on the server

---

## Project Path

```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

## Current Branch

```
feature/langgraph-migration
```

---

## Session Startup

When starting a new session:

1. Verify you're on the server:
```bash
hostname  # Should return: g700data1
```

2. Check git status:
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git branch && git status --short
```

3. Verify Docker services:
```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "table {{.Name}}\t{{.Status}}"
```

---

## Rules

1. All file operations happen directly on the server (no SSH wrapping needed)
2. All paths are server paths (`/home/swebber64/...`)
3. Standard file tools work normally in this environment

---

## Why Remote-SSH

- Eliminates SSH wrapping complexity
- Standard tooling works natively
- No sync issues between Mac and server
- Server has GPU resources (RTX 5080) for running models

---

## LibreChat Custom Endpoints vs Agent Marketplace

**REMEMBER:** These are TWO DIFFERENT FEATURES:

| Feature | Where Agents Appear | How to Add |
|---------|---------------------|------------|
| **Model Dropdown** | Top model selector | Add to `librechat.yaml` endpoints.custom |
| **Agent Marketplace** | Agent marketplace UI | Create agent through LibreChat UI |

**Custom endpoints (like LogoMaker, DHG Visuals) appear in the MODEL DROPDOWN, not the Agent Marketplace.**

If user says "it's not in the marketplace" - tell them to check the MODEL SELECTOR dropdown instead.

