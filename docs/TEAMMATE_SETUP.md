# Teammate Onboarding - DHG AI Factory

Welcome! This guide will get you set up with the Antigravity AI coding environment.

## Prerequisites

- [VSCode](https://code.visualstudio.com/) with [Antigravity extension](https://marketplace.visualstudio.com/items?itemName=Google.antigravity)
- Git installed
- SSH access to the development server (10.0.0.251)

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/sdnydude/dhgaifactory3.5.git
cd dhgaifactory3.5

# 2. Open in VSCode
code .
```

When Antigravity loads, it automatically imports:
- **10 Rules** from `.agent/rules/` (behavioral constraints)
- **14 Workflows** from `.agent/workflows/` (slash commands)
- **Skills** from `.agent/skills/` (extended capabilities)

---

## What You Get

### Rules (Loaded Automatically)
| Rule | Purpose |
|------|---------|
| `debug-discipline.md` | One fix per hypothesis, track attempts |
| `pre-edit-verify.md` | Always view files before editing |
| `server-first.md` | All work on .251 server |
| `strict.md` | No placeholders, no truncation |
| `honesty.md` | Truth over helpfulness |
| `proof-required.md` | Evidence-based debugging |

### Workflows (Slash Commands)
| Command | Purpose |
|---------|---------|
| `/session-start` | Run at start of every session |
| `/commit-flow` | Standardized git commits |
| `/debug-protocol` | Systematic debugging |
| `/agent-check` | Project review and TODO maintenance |
| `/server-work` | Server work patterns |

---

## Required: Server SSH Setup

All development happens on server `10.0.0.251`. You need SSH access:

### 1. Generate SSH Key (if you don't have one)
```bash
ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519_dhg -C "your-email@example.com"
```

### 2. Get Your Public Key Added
Send your public key to the team lead:
```bash
cat ~/.ssh/id_ed25519_dhg.pub
```

### 3. Test Connection
```bash
ssh -i ~/.ssh/id_ed25519_dhg swebber64@10.0.0.251 'echo "Connected!"'
```

### 4. Update Your SSH Key Path
Edit `.agent/rules/server-first.md` and update the SSH key path to your key:
```diff
- SSH Key: `~/.ssh/id_ed25519_fafstudios`
+ SSH Key: `~/.ssh/id_ed25519_dhg`
```

> [!IMPORTANT]
> Do NOT commit this change - it's your local override.

---

## First Session Checklist

1. [ ] Clone repo and open in VSCode
2. [ ] Verify Antigravity extension is active
3. [ ] Run `/session-start` to verify server connection
4. [ ] Check that rules appear in your Antigravity sidebar

---

## Key Principles

These rules govern how Antigravity assists you:

1. **Server-First**: All file edits happen on .251, not locally
2. **No Placeholders**: Every file must be complete, no TODOs
3. **Debug Discipline**: One fix attempt per hypothesis
4. **View Before Edit**: Always read files before modifying

---

## Getting Help

- Check existing workflows: `ls .agent/workflows/`
- Read a workflow: `/workflow-name` in Antigravity
- Project docs: `docs/` folder

Welcome to the team! 🚀
