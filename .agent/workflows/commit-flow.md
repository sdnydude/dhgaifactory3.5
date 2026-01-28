---
description: Standardized git commit workflow for server work
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Git Commit Workflow (Remote-SSH)

// turbo-all

**Environment:** VS Code Remote-SSH on g700data1

---

## Pre-Commit Checklist

- [ ] On correct branch (`feature/langgraph-migration` for active work)
- [ ] No unintended files staged
- [ ] Commit message follows conventional format

---

## 1. Verify Current Branch

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git branch --show-current
```

## 2. Review Changes

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git status --short && echo "" && git diff --stat
```

## 3. Stage Specific Files (NOT git add .)

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add <specific-files>
```

## 4. Commit with Conventional Message

Format: `<type>(<scope>): <description>`

| Type | Use For |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `chore` | Maintenance, dependencies |
| `refactor` | Code restructuring |
| `test` | Adding/updating tests |

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git commit -m "feat(agents): add OpenAI-compatible endpoints"
```

## 5. Push to Remote

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git push origin $(git branch --show-current)
```

---

## Branch Naming

- `feature/<name>` — New features
- `fix/<name>` — Bug fixes
- `docs/<name>` — Documentation

## Never Commit Directly to Master

Master is production-stable. Always use feature branches and merge via PR.
