---
trigger: always_on
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `honesty.md`

# Server-First Development (MANDATORY)

## Critical Rule

All DHG AI Factory project work MUST be performed directly on the server at **10.0.0.251**.

## Pre-Flight Checklist — Run Before EVERY File Operation

Before creating, editing, or modifying any file, verify:

1. **Target path is on 10.0.0.251**, NOT local Mac
2. **Using SSH command**, NOT `write_to_file` or `replace_file_content` tools
3. **Path starts with** `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/` NOT `/tmp`, `/Users`, or any local path

## If About to Use a Local File Tool

- If about to use `write_to_file` → **STOP** → Use SSH `cat >` instead
- If about to use `replace_file_content` → **STOP** → Use SSH with `sed` or `cat >` instead
- If target path is `/tmp` or `/Users` → **STOP** → Redirect to server path

## SSH Command Templates

### Create a new file:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat > /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/path/to/file << "EOF"
file contents here
EOF'
```

### Edit an existing file (append):
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat >> /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/path/to/file << "EOF"
new content
EOF'
```

### View a file:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/path/to/file'
```

### Run commands:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git status'
```

## Server Details

| Property | Value |
|----------|-------|
| **Server IP** | 10.0.0.251 |
| **SSH Key** | `~/.ssh/id_ed25519_fafstudios` |
| **Username** | swebber64 |
| **Project Path** | `/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/` |
| **Active Branch** | `feature/librechat-integration` |

## Exceptions (Require Explicit User Approval)

1. Local `.agent/` files (rules, workflows) — these configure the local development environment
2. Browser-based work (Infisical UI, LibreChat UI, etc.) — runs locally by nature
3. Viewing screenshots or recordings for verification

## Why This Rule Exists

- User preference for all project files to live on the server
- Avoids sync issues and duplicate files across Mac and .251
- Keeps the Mac clean of project artifacts
- Server has GPU resources for running models
