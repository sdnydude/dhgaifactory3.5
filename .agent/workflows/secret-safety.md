---
description: NEVER expose API keys or secrets - strict rules for handling sensitive data
---

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `.agent/rules/honesty.md`

# Secret Safety Protocol (MANDATORY)

## ABSOLUTE PROHIBITIONS

1. **NEVER run commands that output full secrets:**
   - ❌ `cat .env`
   - ❌ `grep API_KEY .env`
   - ❌ `printenv | grep KEY`
   - ❌ `docker inspect` on secret volumes

2. **NEVER display more than 10 characters of any key**

3. **NEVER commit, log, or display secrets in any output**

## SAFE ALTERNATIVES

```bash
# Check if key exists (safe)
printenv OPENAI_API_KEY | wc -c

# Show first 10 chars only (safe)
printenv OPENAI_API_KEY | head -c 10 && echo "...[MASKED]"

# Verify key is set (safe)
[ -n "$OPENAI_API_KEY" ] && echo "SET" || echo "NOT SET"
```

## IF SECRETS ARE ACCIDENTALLY EXPOSED

1. STOP immediately
2. Inform user: "I exposed a secret. Rotate it NOW."
3. Do NOT continue until user confirms rotation

## CONSEQUENCE OF VIOLATION

GitHub will auto-revoke exposed keys, breaking all services.
This has already happened. Never again.
