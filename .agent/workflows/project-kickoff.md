---
description: New project kickoff - interview user and set up project structure
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# New Project Kickoff Workflow (Remote-SSH)

// turbo-all

**Environment:** VS Code Remote-SSH on g700data1

---

## Phase 1: Interview Questions

### Basic Info
1. **Project name** (lowercase, no spaces): ____
2. **Short description** (1 sentence): ____
3. **Primary language/framework**: ____
4. **Project type**: [ ] Web app [ ] API [ ] CLI [ ] Library [ ] Other

### Location
5. **Where should code live?**
   - [ ] Server: `/home/swebber64/DHG/aifactory3.5/<project_name>/`
   - [ ] Other: ____

### Repository
6. **GitHub organization**: [ ] sdnydude [ ] Other: ____
7. **Repo visibility**: [ ] Public [ ] Private
8. **Initial branch name**: [ ] main [ ] master

### Integration
9. **Part of DHG AI Factory?**: [ ] Yes [ ] No
10. **Need LangGraph agent?**: [ ] Yes [ ] No
11. **Need secrets (Infisical)?**: [ ] Yes [ ] No
12. **Need database?**: [ ] Yes [ ] No

---

## Phase 2: Confirm

```
PROJECT SETUP CONFIRMATION
===========================
Name: <project_name>
Description: <description>
Framework: <framework>
Location: <path>
GitHub: <org>/<project_name>
```

**Wait for user approval.**

---

## Phase 3: Create Structure

### 3.1 Create Directory
```bash
mkdir -p /home/swebber64/DHG/aifactory3.5/<project_name>
```

### 3.2 Initialize Git
```bash
cd /home/swebber64/DHG/aifactory3.5/<project_name> && git init && git checkout -b <branch>
```

### 3.3 Create GitHub Repo
```bash
gh repo create <org>/<project_name> --<visibility> --source=. --remote=origin --push
```

---

## Phase 4: Create .agent Config

```bash
mkdir -p /home/swebber64/DHG/aifactory3.5/<project_name>/.agent/{rules,workflows}
cp /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/.agent/rules/honesty.md .agent/rules/
```

---

## Phase 5: Create Standard Files

- README.md
- .gitignore (based on framework)
- docs/TODO.md

---

## Phase 6: Initial Commit

```bash
git add . && git commit -m "chore: initial project setup" && git push -u origin <branch>
```

---

## Phase 7: Report

```
PROJECT KICKOFF COMPLETE
=========================
✓ Directory: /home/swebber64/DHG/aifactory3.5/<project_name>/
✓ GitHub: https://github.com/<org>/<project_name>
✓ Branch: <branch>
✓ Ready for development
```
