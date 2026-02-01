---
description: Secure secrets management with Infisical
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Infisical Secrets Workflow (Remote-SSH)

// turbo-all

**Environment:** VS Code Remote-SSH on g700data1

---

## ⚠️ CRITICAL: Folder Structure

Secrets are organized in folders. You MUST query by path:

| Folder | Contents |
|--------|----------|
| `/infrastructure` | POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB, etc. |
| `/llms` | ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY |
| `/services` | LANGSMITH_API_KEY, PERPLEXITY_API_KEY, NCBI_API_KEY |
| `/` (root) | General config, feature flags |

---

## 1. Query Secrets by Folder

```bash
# List infrastructure secrets
infisical secrets --path="/infrastructure" --env=prod

# List LLM API keys
infisical secrets --path="/llms" --env=prod

# List service keys
infisical secrets --path="/services" --env=prod

# List all folders
infisical secrets folders get --env=prod
```

---

## 2. Get Specific Secret

```bash
# Get a specific secret by name and path
infisical secrets get SECRET_NAME --path="/infrastructure" --env=prod
```

---

## 3. Current Project Configuration

**Workspace ID:** `7509677d-e23d-4262-87ca-64a8cd036b83`
**Config file:** `.infisical.json`
**Default env:** `prod`

---

## 4. Database Credentials (Quick Reference)

From `.env` or Infisical `/infrastructure` folder:
- `POSTGRES_USER` = dhg
- `POSTGRES_DB` = dhg_registry
- `POSTGRES_HOST` = registry-db (in Docker) / localhost (from host)
- `POSTGRES_PORT` = 5432

**Container name:** `986cbb4003b3_dhg-registry-db` or `dhg-registry-db`

---

## 5. Access Infisical Dashboard

- **URL:** https://secrets.digitalharmonyai.com (or https://app.infisical.com)
- **Login:** Manual only (do NOT automate)

---

## 6. NEVER DO

- ❌ Hardcode API keys in code
- ❌ Commit secrets to git
- ❌ Log secret values
- ❌ Display full secrets in output
- ❌ Query root path without checking folders first

---

## 7. Masked Output Only

When showing secrets exist:
```
ANTHROPIC_API_KEY: sk-ant-****...
GOOGLE_API_KEY: AIza****...
```

Never show full values.

---

## 8. If CLI Returns Empty

1. Check you're querying the right folder path
2. Verify workspace ID in `.infisical.json`
3. Try `infisical login` to refresh auth
4. Check secrets via web UI as fallback
5. Fall back to `.env` file for local development

