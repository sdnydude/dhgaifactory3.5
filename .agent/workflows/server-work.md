---
description: All DHG AI Factory work must be done on .251 server
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Server-First Development Workflow

// turbo-all

## MANDATORY: All work for the DHG AI Factory project MUST be performed directly on the server at 10.0.0.251

---

## Pre-Flight Checklist (Run Before ANY File Operation)

Before EVERY file create/edit:

1. ☐ Target path is on 10.0.0.251, NOT local Mac?
2. ☐ Using SSH command, NOT write_to_file tool?
3. ☐ Path starts with `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/`?

If any answer is NO → STOP and redirect to server.

---

## Session Startup

When starting a new session on this project:

1. Verify SSH connectivity:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'echo "Connected to .251"'
```

2. Check git status on server:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git branch && git status --short'
```

3. Verify Docker services:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && docker compose ps --format "table {{.Name}}\t{{.Status}}"'
```

---

## Rules:

1. **DO NOT** create files on the local Mac and copy them to .251
2. **DO NOT** write code, configs, or documentation to `/tmp` or local paths
3. **ALL** file creation, editing, and commands must execute directly on 10.0.0.251 via SSH
4. If you need to create a file, use: `ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat > /path/to/file << EOF ... EOF'`
5. If you need to edit a file, use sed/vim via SSH or read/modify/write via SSH

---

## Exceptions (require explicit user approval):

- Browser-based work (Infisical UI, LibreChat UI, etc.) - runs locally by nature
- Viewing screenshots or recordings for verification
- Local `.agent/` files (rules, workflows) - configure local dev environment

---

## SSH Connection:

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251
```

## Project Path on Server:

```
/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/
```

## Current Branch:

```
feature/librechat-integration
```

---

## Why:

- User preference for all project files to live on the server
- Avoids sync issues and duplicate files
- Keeps the Mac clean of project artifacts
- Server has GPU resources (RTX 5080) for running models

---

## File Creation on .251

**ALWAYS use interactive SSH for creating/editing files:**

1. SSH into the server
2. Use nano or vim to edit
3. Save and exit

**NEVER:**
- Create files on Mac and scp to .251
- Use heredocs for complex multi-line files (quoting breaks)

**If heredoc is needed:** Use single-quoted delimiter to prevent variable expansion:
```bash
ssh swebber64@10.0.0.251 'cat > /path/to/file << '\''EOF'\''
content here
EOF'
```

---

## LibreChat Custom Endpoints vs Agent Marketplace

**REMEMBER:** These are TWO DIFFERENT FEATURES:

| Feature | Where Agents Appear | How to Add |
|---------|---------------------|------------|
| **Model Dropdown** | Top model selector | Add to `librechat.yaml` endpoints.custom |
| **Agent Marketplace** | Agent marketplace UI | Create agent through LibreChat UI |

**Custom endpoints (like LogoMaker, DHG Visuals) appear in the MODEL DROPDOWN, not the Agent Marketplace.**

If user says "it's not in the marketplace" - tell them to check the MODEL SELECTOR dropdown instead.

If user SPECIFICALLY wants Agent Marketplace - that requires creating an agent through LibreChat's built-in agent builder UI using a backing model.
