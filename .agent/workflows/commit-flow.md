---
description: Standardized git commit workflow for server work
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Git Commit Workflow

// turbo-all

Use this workflow when committing changes on the .251 server.

---

## Pre-Commit Checklist

Before committing, verify:
- [ ] On correct branch (`feature/librechat-integration` for active work)
- [ ] No unintended files staged
- [ ] Commit message follows conventional format

---

## 1. Verify Current Branch

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git branch --show-current'
```

Expected: `feature/librechat-integration` (or other feature branch, NOT `master` for active work)

## 2. Review Changes

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git status --short && echo "" && git diff --stat'
```

## 3. Stage Specific Files (NOT git add .)

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add <specific-files>'
```

## 4. Commit with Conventional Message

Format: `<type>(<scope>): <description>`

Types:
- `feat` — New feature
- `fix` — Bug fix
- `docs` — Documentation only
- `chore` — Maintenance, dependencies
- `refactor` — Code change that neither fixes bug nor adds feature
- `test` — Adding or updating tests

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git commit -m "feat(agents): add OpenAI-compatible endpoints for LibreChat"'
```

## 5. Push to Remote

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git push origin $(git branch --show-current)'
```

---

## Branch Naming Convention

- `feature/<name>` — New features
- `fix/<name>` — Bug fixes
- `docs/<name>` — Documentation updates
- `refactor/<name>` — Code refactoring

## Never Commit Directly to Master

Master is production-stable. Always work on feature branches and merge via PR.
