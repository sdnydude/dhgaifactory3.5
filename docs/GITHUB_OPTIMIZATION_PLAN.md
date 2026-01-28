# GitHub Optimization Plan for DHG AI Factory

**Date:** 2026-01-27  
**Goal:** Transform GitHub from passive storage to active development accelerator

---

## Current State

- No `.github/` directory
- No workflows, no CI/CD
- Manual deployments via SSH
- No automated testing
- No issue templates or PR templates

---

## Proposed Setup

### 1. Repository Structure

```
.github/
├── workflows/
│   ├── ci.yml                 # Lint + test on every PR
│   ├── docker-build.yml       # Build images on tag/release
│   ├── deploy-staging.yml     # Auto-deploy to staging on merge
│   └── security-scan.yml      # Dependency + container scanning
├── ISSUE_TEMPLATE/
│   ├── bug_report.md
│   ├── feature_request.md
│   └── agent_enhancement.md
├── PULL_REQUEST_TEMPLATE.md
├── CODEOWNERS
└── dependabot.yml
```

---

### 2. Workflows That Benefit Both of Us

#### A. CI Pipeline (`ci.yml`)
**Trigger:** Every PR, every push to main  
**Benefits:**
- Catches syntax errors before merge
- Validates Docker builds
- Runs unit tests if present
- YOU: Confidence that code works
- ME: Clear signal if my changes break something

```yaml
# Runs: ruff lint, mypy type check, pytest
# Checks: Docker Compose syntax validation
# Time: ~2-3 minutes
```

#### B. Docker Build (`docker-build.yml`)
**Trigger:** Git tags (v*), manual dispatch  
**Benefits:**
- Consistent image builds
- Tags images with git SHA + version
- Pushes to your registry (if configured)
- YOU: One-click deployable artifacts
- ME: Can verify container builds without SSH

#### C. Deploy to Staging (`deploy-staging.yml`)
**Trigger:** Merge to main  
**Benefits:**
- Auto-deploys to .251 via SSH action
- Runs health checks post-deploy
- Notifies on success/failure
- YOU: Zero-touch staging deployments
- ME: Immediate feedback on deployment success

#### D. Security Scanning (`security-scan.yml`)
**Trigger:** Weekly + on PR  
**Benefits:**
- Trivy container scanning
- pip-audit for Python deps
- npm audit for JS deps
- YOU: CVE alerts before production
- ME: Can flag security issues proactively

---

### 3. Issue & PR Templates

#### Issue Templates
- **Bug Report:** Structured format for reproducing issues
- **Feature Request:** Business value + acceptance criteria
- **Agent Enhancement:** Specific to DHG agent improvements

#### PR Template
```markdown
## What does this PR do?
## How was this tested?
## Checklist
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No secrets committed
```

---

### 4. Branch Protection Rules

| Branch | Rules |
|--------|-------|
| `main` | Require PR, require CI pass, no force push |
| `feature/*` | Allow force push, no requirements |
| `release/*` | Require 1 approval + CI pass |

---

### 5. CODEOWNERS

```
# Default owner
* @swebber64

# Agent code requires review
/agents/ @swebber64
/services/ @swebber64

# Docs can be more relaxed
/docs/ @swebber64
```

---

### 6. Dependabot Configuration

```yaml
# Weekly updates for:
- pip (Python)
- npm (JavaScript)
- docker (base images)
- github-actions (workflow actions)
```

---

### 7. GitHub Actions Secrets Required

| Secret | Purpose |
|--------|---------|
| `SSH_PRIVATE_KEY` | Deploy to .251 |
| `SSH_HOST` | 10.0.0.251 (or Tailscale IP) |
| `SSH_USER` | swebber64 |
| `DOCKER_REGISTRY_TOKEN` | Push images (optional) |
| `SLACK_WEBHOOK` | Deployment notifications (optional) |

---

## Implementation Order

### Phase 1: Foundation (Day 1)
1. [ ] Create `.github/` directory structure
2. [ ] Add basic `ci.yml` workflow
3. [ ] Add PR template
4. [ ] Set up branch protection on main

### Phase 2: Automation (Day 2)
5. [ ] Add `docker-build.yml` workflow
6. [ ] Add `deploy-staging.yml` workflow
7. [ ] Configure GitHub Secrets
8. [ ] Test end-to-end: PR → merge → deploy

### Phase 3: Polish (Day 3)
9. [ ] Add issue templates
10. [ ] Configure Dependabot
11. [ ] Add security scanning
12. [ ] Add CODEOWNERS

---

## Expected Outcomes

| Before | After |
|--------|-------|
| Manual SSH deployments | Auto-deploy on merge |
| No validation before merge | CI catches errors early |
| Unknown security posture | Weekly vulnerability scans |
| Ad-hoc issue tracking | Structured templates |
| No code ownership | Clear CODEOWNERS file |

---

## Decision Points for You

1. **Docker Registry:** Push to Docker Hub, GHCR, or self-hosted?
2. **Notifications:** Slack, email, or both?
3. **Auto-Deploy:** Enable for staging only, or also production?
4. **Branch Strategy:** main + feature, or main + develop + feature?

---

## Next Step

Approve this plan, then I will create the `.github/` directory and all files on .251.
