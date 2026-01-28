---
description: Git and GitHub operations - branching, commits, push, merge, cleanup
---

# Git & GitHub Workflow

// turbo-all

> Run these commands on .251 via SSH

---

## 1. Check Status (Run First)

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "=== BRANCH ===" && git branch --show-current && echo "" && echo "=== STATUS ===" && git status --short && echo "" && echo "=== LAST 3 COMMITS ===" && git log --oneline -3'
```

---

## 2. Commit Changes

### Stage all and commit
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git add -A && git commit -m "YOUR_MESSAGE_HERE"'
```

### Commit message prefixes
- `feat:` — New feature
- `fix:` — Bug fix  
- `docs:` — Documentation only
- `chore:` — Maintenance

---

## 3. Push to GitHub

### Normal push
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git push origin $(git branch --show-current)'
```

### Force push (after rebase)
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git push origin $(git branch --show-current) --force'
```

---

## 4. Sync with Master

### Rebase onto master (recommended)
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git fetch origin master && git rebase origin/master'
```

---

## 5. Branch Management

### List all branches
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git branch -a'
```

### Create new branch
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git checkout -b feature/NEW_BRANCH'
```

### Delete remote branch
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git push origin --delete BRANCH_NAME'
```

---

## 6. Undo Mistakes

### Undo last commit (keep changes)
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && git reset HEAD~1 --soft'
```

---

## 7. Handle Large Files

### Add to .gitignore
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5 && echo "FOLDER/" >> .gitignore && git add .gitignore && git commit -m "chore: gitignore FOLDER"'
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Check status | git status |
| Stage all | git add -A |
| Commit | git commit -m "msg" |
| Push | git push origin BRANCH |
| Rebase | git rebase origin/master |
| Force push | git push --force |
