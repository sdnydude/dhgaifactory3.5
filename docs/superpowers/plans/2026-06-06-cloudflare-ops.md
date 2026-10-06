# cloudflare-ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A user-level Claude Code skill that lets Claude directly read/write/edit all of Cloudflare (Access, DNS, tunnels incl. ingress, Workers/R2/KV/D1) via the official Cloudflare MCP, with one in-line confirm on destructive ops.

**Architecture:** Official hosted `cloudflare/mcp` (HTTP, Code Mode ON = `search`/`execute`) authed by a write-capable API token supplied as an env reference (token lives in Doppler, never in a file). A thin user-level skill (`~/.claude/skills/cloudflare-ops/SKILL.md`) classifies each request (read / routine write / destructive), gates destructive ops behind one in-line confirm + diff, resolves resource IDs live, and ships one playbook: `access-login <host> on|off`. Tunnel ingress is brought under the API by migrating both tunnels to remote-managed config.

**Tech Stack:** Claude Code skills + MCP; Cloudflare API v4; Doppler (`dhg-infra`); `cloudflared`; `curl` for verification.

**Spec:** `docs/superpowers/specs/2026-06-06-cloudflare-ops-design.md` (decisions D1–D7).

**Note on test style:** this skill is markdown + MCP config, not a code library — so "tests" are real integration verifications (MCP calls, `curl` redirect checks), each with an exact command and expected output. There are no unit tests to write; do not fabricate any.

---

## Phase 1 — Token + MCP wiring

### Task 1: Mint the write-capable token and store it in Doppler

**Files:** none (Cloudflare dashboard + Doppler). Stephen runs this; Claude cannot mint tokens.

- [ ] **Step 1: Create the API token**

In the Cloudflare dashboard → Profile → API Tokens → Create Token → Custom token, with permissions:
- Account · Access: Apps and Policies · **Edit**
- Account · Cloudflare Tunnel · **Edit**
- Account · Workers Scripts · **Edit**, Workers KV Storage · **Edit**, Workers R2 Storage · **Edit**, D1 · **Edit**, Pages · **Edit**
- Zone · DNS · **Edit**, Zone · Zone · **Read** (zone: `digitalharmonyai.com`)

- [ ] **Step 2: Store it in Doppler**

```bash
doppler secrets set CLOUDFLARE_API_TOKEN --project dhg-infra --config dev
# paste the token at the prompt (do NOT pass it on the command line)
```

- [ ] **Step 3: Verify it's stored (masked)**

Run: `doppler secrets get CLOUDFLARE_API_TOKEN --project dhg-infra --config dev --plain | cut -c1-6` 
Expected: first 6 chars print, rest hidden. (Never print the full value.)

- [ ] **Step 4: Smoke-test the token against the Cloudflare API**

```bash
doppler run --project dhg-infra --config dev -- \
  curl -s -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
  https://api.cloudflare.com/client/v4/user/tokens/verify
```
Expected: JSON `"success": true` and `"status": "active"`.

---

### Task 2: Register the Cloudflare MCP server with Claude Code

**Files:**
- Modify: `~/.claude/settings.json` (env reference) — or launch wrapper
- MCP registry (via `claude mcp add`)

- [ ] **Step 1: Make the token available to Claude's environment as an env var**

Add to `~/.claude/settings.json` under `"env"` a reference resolved from Doppler at launch, OR launch Claude via Doppler. Pin the launch-via-Doppler approach (keeps the literal token out of every file):

```bash
# Stephen launches Claude Code in this project with the token in env:
doppler run --project dhg-infra --config dev -- claude
```

- [ ] **Step 2: Add the MCP server (Code Mode ON = default URL), header references the env var**

```bash
claude mcp add --scope user --transport http cloudflare \
  https://mcp.cloudflare.com/mcp \
  --header "Authorization: Bearer \${CLOUDFLARE_API_TOKEN}"
```
The literal `${CLOUDFLARE_API_TOKEN}` is stored (an env reference), not the secret.

- [ ] **Step 3: Verify the server connects and exposes Code Mode tools**

Run: `claude mcp list`
Expected: `cloudflare` listed as connected. The tool surface shows `search` and `execute` (Code Mode ON), not ~2,500 tools.

- [ ] **Step 4: Verify a live READ through the MCP**

In a Claude session, ask the MCP to list Access applications (via `search`→`execute` against `GET /accounts/{account_id}/access/apps`).
Expected: the wildcard `*.digitalharmonyai.com` app appears, with its `aud` and `id`.

- [ ] **Step 5: Commit the settings change**

```bash
git -C ~/.claude add settings.json 2>/dev/null || true   # if ~/.claude is version-controlled
# (project repo has no change yet; skill files come in Phase 2)
```

---

## Phase 2 — Skill scaffold

### Task 3: Create the `cloudflare-ops` skill with op-classification + confirm gate

**Files:**
- Create: `~/.claude/skills/cloudflare-ops/SKILL.md`

- [ ] **Step 1: Write `SKILL.md`**

```markdown
---
name: cloudflare-ops
description: Read/write/edit Stephen's Cloudflare setup (Access, DNS, tunnels incl. ingress, Workers/R2/KV/D1) via the cloudflare MCP. Use for any request to view or change Cloudflare — Access login toggles, DNS records, tunnel routes, Workers/R2/KV/D1. Reads are automatic; destructive changes ask once with a diff.
---

# cloudflare-ops

Execute Cloudflare changes via the `cloudflare` MCP (tools: `search`, `execute`).
Resolve every endpoint by calling `search` first, then `execute` with
`cloudflare.request(...)`. The account is the single DHG account; resolve the
account_id live via `GET /accounts`. Zone is `digitalharmonyai.com`.

## Resolve live — never cache
Never hardcode account IDs, zone IDs, Access app IDs, audience tags, or tunnel IDs.
Resolve them at call time from the API. (Illustrative IDs in chat are fine; never
bake them into a stored procedure.)

## Classify every request, then act
- **Read** (list/get): execute immediately, no confirmation.
- **Routine write** (create DNS record; create Access app; deploy/update a Worker;
  write a KV/R2 key; add a tunnel ingress route): execute, then report what changed.
- **Destructive write** — ALWAYS confirm once with a before/after diff, then execute:
  - edit/weaken an Access **policy** (auth-affecting)
  - delete or repoint a DNS record
  - delete an Access app
  - delete a Worker / Pages project
  - delete an R2 bucket / KV namespace / D1 database, or bulk-delete data
  - delete or disable a tunnel; remove an ingress route

## Confirm format (destructive only)
Show: the resource (resolved name + id), the exact field change (before → after),
and the blast radius. Then ask: "Proceed? (yes/no)". Execute only on explicit yes.

## All writes are desired-state
Read current state → compute the diff → converge. Re-running at desired state is a
no-op. Never blind-flip.

## Audit
Writes are Cloudflare API calls and appear in Cloudflare Audit Logs (the
authoritative record). Do not write a local audit file.

## Kill-switch
If Cloudflare access must be cut: rotate CLOUDFLARE_API_TOKEN in Doppler
(`dhg-infra/dev`) and revoke it in the dashboard.

## Playbooks
- access-login: see ./playbooks/access-login.md
```

- [ ] **Step 2: Verify the skill loads**

Run: `claude` then check the skill list includes `cloudflare-ops` (or `ls ~/.claude/skills/cloudflare-ops/SKILL.md`).
Expected: file exists; skill appears in the available-skills list.

- [ ] **Step 3: Commit**

```bash
cd ~/.claude/skills/cloudflare-ops && git init -q 2>/dev/null; \
git -C ~/.claude add skills/cloudflare-ops/SKILL.md 2>/dev/null || true
```
(If `~/.claude/skills` isn't a repo, skip git; the file on disk is the deliverable.)

---

## Phase 3 — access-login playbook (the motivating use case)

### Task 4: Write the `access-login` playbook

**Files:**
- Create: `~/.claude/skills/cloudflare-ops/playbooks/access-login.md`

- [ ] **Step 1: Write the playbook**

```markdown
# Playbook: access-login <host> on|off

Toggle Cloudflare Zero Trust Access login for <host>. This is a DESTRUCTIVE op
(it changes authentication) — always confirm with a diff.

## Steps
1. Resolve the Access application gating <host>:
   - `GET /accounts/{account_id}/access/apps` → find the app whose domain matches
     <host> (today: the wildcard `*.digitalharmonyai.com`).
2. **Blast-radius check:** if the matched app is the wildcard, state explicitly that
   this changes login for ALL `*.digitalharmonyai.com` subdomains, not just <host>.
   Include this in the confirm.
3. Read the app's current policies:
   `GET /accounts/{account_id}/access/apps/{app_id}/policies`
   (or the reusable policy at Access → Policies if the app uses one).
4. Compute desired state:
   - **off** = the gating policy has `decision: "bypass"` with an Include rule
     `everyone` (`{"include":[{"everyone":{}}]}`).
   - **on**  = the gating policy has `decision: "allow"` with the original identity
     Include (emails ending in `@digitalharmonyai.com` / the company-domain rule).
   - If already at desired state → no-op.
5. Show the diff (app name+id, policy decision before→after, blast radius). Confirm.
6. On yes, converge:
   - update the existing policy's `decision`/`include` via
     `PUT /accounts/{account_id}/access/apps/{app_id}/policies/{policy_id}`
     (or the reusable-policy PUT under `/access/policies/{policy_id}` if reusable).
7. Verify:
   `curl -s -o /dev/null -w "%{http_code}" https://<host>`
   - off → expect `200` (origin served; no login redirect)
   - on  → expect `302` (redirect to `*.cloudflareaccess.com`)
8. If `on` ever fails after an `off`, immediately re-run `access-login <host> on`
   to restore the gate (no open public-exposure window).
```

- [ ] **Step 2: Verify the file exists**

Run: `ls ~/.claude/skills/cloudflare-ops/playbooks/access-login.md`
Expected: path prints.

### Task 5: End-to-end test `access-login` on `docs`

- [ ] **Step 1: Baseline — confirm login is currently ON**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://docs.digitalharmonyai.com`
Expected: `302` (redirects to cloudflareaccess.com).

- [ ] **Step 2: Run the playbook OFF (through the skill, with confirm)**

In a Claude session: "access-login docs off". Confirm at the prompt.
Expected: the skill resolves the wildcard app, shows the blast-radius diff, executes the Bypass/Everyone policy update.

- [ ] **Step 3: Verify OFF**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://docs.digitalharmonyai.com`
Expected: `200` (origin served, no redirect). Allow up to ~60s for propagation; re-run if still 302.

- [ ] **Step 4: Run the playbook ON (restore)**

In a Claude session: "access-login docs on". Confirm.

- [ ] **Step 5: Verify ON**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://docs.digitalharmonyai.com`
Expected: `302` (gate restored).

- [ ] **Step 6: Idempotency check**

Run "access-login docs on" again.
Expected: skill reports already at desired state → no-op, no write.

---

## Phase 4 — Tunnel ingress under the API (remote-managed migration)

### Task 6: Migrate both tunnels to remote-managed config

**Files:**
- Read: `/etc/cloudflared/config.yml`, `/etc/cloudflared/config-portage.yml` (current ingress)
- Modify (Stephen, root, in his Apple Terminal SSH session): the two systemd units + retire ingress from the local YAML

> Why: locally-managed tunnels keep ingress in the root-owned YAML, which the API/token can't touch. Remote-managed tunnels store ingress in Cloudflare → editable via the MCP token like everything else. Decision D3.

- [ ] **Step 1: Capture current ingress (both tunnels)**

Run: `grep -A2 hostname /etc/cloudflared/config.yml /etc/cloudflared/config-portage.yml`
Record every `hostname → service` mapping (these become the remote config).

- [ ] **Step 2: Set the remote configuration for each tunnel via the MCP**

In a Claude session, for each tunnel id, `execute`:
`PUT /accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations` with body
`{"config":{"ingress":[ {<each hostname→service from Step 1>}, {"service":"http_status:404"} ]}}`.
(Resolve `tunnel_id` via `GET /accounts/{account_id}/cfd_tunnel`; resolve the exact endpoint via MCP `search` first.)
Expected: `"success": true` for each tunnel.

- [ ] **Step 3: Verify the remote config took**

In a Claude session, `execute` `GET /accounts/{account_id}/cfd_tunnel/{tunnel_id}/configurations` for each tunnel.
Expected: the returned ingress matches Step 1's mappings + the 404 catch-all.

- [ ] **Step 4: Switch the connector to remote-managed (Stephen, root)**

Confirm the exact run flag first: `cloudflared tunnel run --help` (remote-managed = run by tunnel name/token with NO `--config`/`credentials-file` ingress).
Then edit each systemd unit's `ExecStart` to run the tunnel without the local ingress config, e.g.:
```
ExecStart=/usr/local/bin/cloudflared tunnel run <TUNNEL_NAME>
```
Reload + restart:
```bash
sudo systemctl daemon-reload
sudo systemctl restart cloudflared cloudflared-portage
```

- [ ] **Step 5: Verify every existing hostname still resolves**

Run for each migrated hostname (example):
```bash
for h in app vs registry docs portage portage-api rehearsal otel; do \
  echo -n "$h: "; curl -s -o /dev/null -w "%{http_code}\n" https://$h.digitalharmonyai.com; done
```
Expected: each returns its normal status (200 or 302-to-access), none `530`/`502`.

### Task 7: Verify ingress create/remove through the skill (no sudo)

- [ ] **Step 1: Add a throwaway ingress route via the skill**

In a Claude session: "expose test.digitalharmonyai.com to localhost:8017".
Expected: routine write — skill PUTs updated remote config (adds the route before the 404), reports success, no sudo.

- [ ] **Step 2: Verify it resolves**

Run: `curl -s -o /dev/null -w "%{http_code}\n" https://test.digitalharmonyai.com`
Expected: a backend status (not `530`), proving the route is live. (Add a DNS record first if needed — the skill does this as a routine write.)

- [ ] **Step 3: Remove the route via the skill (destructive → confirm)**

In a Claude session: "remove the test.digitalharmonyai.com ingress route". Confirm.
Expected: skill shows diff, removes the route on yes.

---

## Phase 5 — Full DoD verification

### Task 8: Coverage + safety smoke

- [ ] **Step 1: Read across products**

In a Claude session, list Access apps, DNS records (zone `digitalharmonyai.com`), and one dev-platform resource (e.g. KV namespaces).
Expected: all succeed via the MCP.

- [ ] **Step 2: Routine write + confirm-on-destructive**

Create a TXT DNS record `_cfops-test.digitalharmonyai.com` (routine — no confirm), then delete it (destructive — must prompt, show diff, execute on yes).
Verify: `dig +short TXT _cfops-test.digitalharmonyai.com` returns the value after create, empty after delete.

- [ ] **Step 3: Kill-switch drill**

Rotate the token: in Doppler set a new `CLOUDFLARE_API_TOKEN` (or revoke+recreate in dashboard), restart Claude's env, and confirm a read now fails until the new token is in place.
Expected: with the old token revoked, MCP calls return auth errors — proving rotation cuts agent access.

- [ ] **Step 4: Commit the skill + plan completion**

```bash
cd /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5
git add docs/superpowers/plans/2026-06-06-cloudflare-ops.md
git commit -m "docs(plan): cloudflare-ops implementation plan"
```

---

## Self-review notes
- **Spec coverage:** D1 (skill, Task 3) · D2 (MCP+token, Tasks 1–2) · D3 (remote-managed ingress, Task 6) · D4 (access-login bypass/allow, Tasks 4–5) · D5 (resolve-live, Task 3 SKILL.md) · D6 (one playbook, Task 4) · D7 (audit=CF logs + token kill-switch, Task 3 + Task 8 Step 3). All covered.
- **No deferrals:** ingress is migrated and tested (Phase 4), not parked. The only "look it up" step is `cloudflared tunnel run --help` (Task 6 Step 4) — confirming an exact run flag for a root systemctl change Stephen executes; the decision (remote-managed) is fixed.
- **Secrets:** token only in Doppler; config files hold the env reference `${CLOUDFLARE_API_TOKEN}`, never the literal.
```
