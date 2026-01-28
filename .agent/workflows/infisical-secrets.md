---
description: Secure secrets management with Infisical
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Infisical Secrets Workflow (Remote-SSH)

// turbo-all

**Environment:** VS Code Remote-SSH on g700data1

---

## 1. Access Infisical Dashboard

- **URL:** https://secrets.digitalharmonyai.com (or https://app.infisical.com)
- **Login:** Manual only (do NOT automate)

---

## 2. Retrieve Secret for Use

```bash
# Using Infisical CLI (if installed)
infisical secrets get SECRET_NAME --env=prod
```

---

## 3. Add New Secret

**Via UI only** - always add secrets through the Infisical web UI, never hardcode.

---

## 4. Environment Variables on Server

Secrets injected at runtime via:
- `.env` files (gitignored)
- Docker env vars
- Infisical SDK

---

## 5. NEVER DO

- ❌ Hardcode API keys in code
- ❌ Commit secrets to git
- ❌ Log secret values
- ❌ Display full secrets in output

---

## 6. Masked Output Only

When showing secrets exist:
```
ANTHROPIC_API_KEY: sk-ant-****...
GOOGLE_API_KEY: AIza****...
```

Never show full values.

---

## Current Project Secrets

| Secret | Storage | Notes |
|--------|---------|-------|
| ANTHROPIC_API_KEY | Infisical | Claude API |
| GOOGLE_API_KEY | Infisical | Gemini API |
| PERPLEXITY_API_KEY | Infisical | Web search |
| NCBI_API_KEY | Infisical | PubMed |
| LANGSMITH_API_KEY | Infisical | LangSmith Cloud |
