---
description: New project kickoff - interview user and set up project structure
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# New Project Kickoff Workflow

Use this workflow when starting a brand new project.

---

## Phase 1: Interview Questions

Ask the user these questions before proceeding:

### Basic Info
1. **Project name** (lowercase, no spaces): ____
2. **Short description** (1 sentence): ____
3. **Primary language/framework**: ____
4. **Project type**: [ ] Web app [ ] API [ ] CLI [ ] Library [ ] Other

### Location
5. **Where should code live?**
   - [ ] Server (.251): `/home/swebber64/DHG/aifactory3.5/<project_name>/`
   - [ ] Local Mac: `/Users/swebber64/<path>/`
   - [ ] Other: ____

### Repository
6. **GitHub organization**: [ ] sdnydude [ ] Other: ____
7. **Repo visibility**: [ ] Public [ ] Private
8. **Initial branch name**: [ ] main [ ] master [ ] Other: ____

### Development
9. **Primary model for assistance**: [ ] Claude [ ] Gemini [ ] Both
10. **Need secrets management?**: [ ] Yes (Infisical) [ ] No
11. **Need database?**: [ ] Yes (PostgreSQL) [ ] No [ ] Other: ____

### AI Factory Integration
12. **Part of DHG AI Factory?**: [ ] Yes [ ] No
13. **Need LangGraph agent?**: [ ] Yes [ ] No
14. **Need Registry integration?**: [ ] Yes [ ] No

---

## Phase 2: Confirm Answers

After collecting answers, summarize:

```
PROJECT SETUP CONFIRMATION
===========================
Name: <project_name>
Description: <description>
Framework: <framework>
Location: <path>
GitHub: <org>/<project_name>
Visibility: <public/private>
Branch: <branch>
Secrets: <yes/no>
Database: <yes/no>
AI Factory: <yes/no>
```

**Wait for user approval before proceeding.**

---

## Phase 3: Create Project Structure

### 3.1 Create Directory
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'mkdir -p /home/swebber64/DHG/aifactory3.5/<project_name>'
```

### 3.2 Initialize Git
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/<project_name> && git init && git checkout -b <branch>'
```

### 3.3 Create GitHub Repo
```bash
# Using GitHub CLI
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'gh repo create <org>/<project_name> --<visibility> --source=/home/swebber64/DHG/aifactory3.5/<project_name> --remote=origin --push'
```

---

## Phase 4: Create Antigravity Config

### 4.1 Create .agent folder
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'mkdir -p /home/swebber64/DHG/aifactory3.5/<project_name>/.agent/{rules,workflows}'
```

### 4.2 Copy Core Rules
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cp /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/.agent/rules/honesty.md /home/swebber64/DHG/aifactory3.5/<project_name>/.agent/rules/'
```

### 4.3 Create Project-Specific Config
Create `.agent/project-context.md` with:
```markdown
# Project: <project_name>

## Description
<description>

## Tech Stack
- Language: <language>
- Framework: <framework>
- Database: <database>

## Key Paths
- Code: /home/swebber64/DHG/aifactory3.5/<project_name>/
- Docs: /home/swebber64/DHG/aifactory3.5/<project_name>/docs/

## External Services
- Secrets: <Infisical/None>
- Registry: <CR/None>
- Models: <Claude/Gemini/Ollama>

## Development Notes
<any special instructions>
```

---

## Phase 5: Create Standard Files

### 5.1 README.md
```markdown
# <project_name>

<description>

## Setup

TBD

## Usage

TBD
```

### 5.2 .gitignore
Based on language/framework chosen.

### 5.3 docs/TODO.md
```markdown
# <project_name> - TODO

## P0: Setup
- [ ] Initial project structure
- [ ] Environment configuration
- [ ] First feature

## P1: Next Steps
- [ ] TBD
```

---

## Phase 6: Initial Commit

```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cd /home/swebber64/DHG/aifactory3.5/<project_name> && git add . && git commit -m "chore: initial project setup" && git push -u origin <branch>'
```

---

## Phase 7: Report to User

```
PROJECT KICKOFF COMPLETE
=========================

✓ Directory created: /home/swebber64/DHG/aifactory3.5/<project_name>/
✓ Git initialized on branch: <branch>
✓ GitHub repo: https://github.com/<org>/<project_name>
✓ Antigravity config: .agent/ folder ready
✓ Initial commit pushed

Ready to start development.
```

---

## Optional: If AI Factory Project

### Register with Central Registry
```bash
# Add to registry database
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'curl -X POST http://localhost:8011/api/v1/projects -H "Content-Type: application/json" -d "{\"name\": \"<project_name>\", \"description\": \"<description>\"}"'
```

### Create LangGraph Scaffold
If LangGraph agent needed, create:
- `langgraph.json`
- `src/agent.py`
- `requirements.txt`
