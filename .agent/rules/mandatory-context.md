

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `honesty.md`

# Mandatory Context Retrieval (ENFORCED)

## BEFORE EVERY RESPONSE

**You MUST do these things BEFORE responding to ANY user message:**

### 1. Read Pre-Response Workflow
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 'cat /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/.agent/workflows/pre-response.md'
```
Then FOLLOW every instruction in it.

### 2. Query CR Database for Lost Context
At the START of every session, query the CR database for relevant prior conversations:
```bash
ssh -i ~/.ssh/id_ed25519_fafstudios swebber64@10.0.0.251 "docker exec 986cbb4003b3_dhg-registry-db psql -U dhg -d dhg_registry -t -c \"SELECT LEFT(content, 2000) FROM antigravity_messages WHERE content ILIKE '%TOPIC%' ORDER BY created_at DESC LIMIT 5;\""
```
Replace `TOPIC` with keywords from the user's request.

### 3. Do NOT Skip These Steps
- Do not assume you remember
- Do not proceed without querying if context might exist
- Do not claim completion without verification

## Violations

If you skip these steps, you will:
- Forget critical context the user already gave you
- Waste the user's time re-explaining things
- Produce incorrect or incomplete work

## The User Built a Database For You

The CR database contains prior conversation history. USE IT.
