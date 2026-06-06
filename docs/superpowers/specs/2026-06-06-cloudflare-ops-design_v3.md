# cloudflare-ops — Design Spec (full-capability)

**Date:** 2026-06-06
**Status:** Active design — pending spec review → implementation plan
**Author:** Claude (Opus 4.8) + Stephen Webber
**Reviewers:** security-auditor + systems-architect advisor subagents (two passes, 2026-06-06)

## Intent (corrected)

Stephen wants Claude to **directly read, write, and edit his entire Cloudflare setup** on request
— **scope C, full CRUD**: Zero Trust Access apps/policies, DNS, tunnels, Workers/Pages/R2/KV/D1.
Claude **executes** the changes itself (write-capable token); it does **not** prepare commands for
manual paste. The recurring concrete pain that motivated this — toggling Access login on/off for a
subdomain — is a write, and Claude should just do it.

**Risk decision (Stephen's call, explicit):** a write-capable token held by an LLM agent carries a
prompt-injection blast radius (advisors flagged this). On a single-user dev server, Stephen accepts
that risk in exchange for full capability. Mitigations he *did* choose: **one in-line confirm on
destructive ops**, Cloudflare Audit Logs, and a token-rotation kill-switch. We do not gate
everything behind out-of-band confirms.

## Prior draft history

- `..._v1.md` — original 3-layer draft (MCP + skill + root daemon, one broad token, Code Mode OFF).
- `..._v2.md` — over-scoped-down "safe v1" (read-only token, human-executes writes). **Rejected by
  Stephen** as not delivering the planned capability. This file replaces it with full scope C.

## Confirmation model (the core behavior)

| Op class | Examples | Behavior |
|---|---|---|
| **Read** | list/get anything | Auto, no confirm |
| **Routine write** | create DNS record, create Access app, deploy/update a Worker, write a KV/R2 key | Auto-execute, show what was done |
| **Destructive write** | **edit/weaken an Access policy** (auth-affecting), delete or repoint a DNS record, delete an Access app, delete a Worker/Pages project, delete an R2 bucket / KV namespace / D1 database or bulk-delete data, delete/disable a tunnel | **One in-line confirm** with a before/after diff, then execute |

- The confirm is in-line (sufficient per Stephen's risk decision; not out-of-band).
- The **Access-policy edit is always destructive** — it can un-auth public services — so it always
  confirms, with an explicit blast-radius note (see wildcard caveat).
- All writes are **desired-state / idempotent** (read current → diff → converge), never blind flips.

## Environment facts (verified)

- Server `g700data1` (10.0.0.251), user `swebber64`. Claude's Bash tool is non-interactive (no PTY);
  `sudo -n` requires a password; `!`-paste can't do interactive auth.
- Wildcard Zero Trust Access app gates all `*.digitalharmonyai.com` (team
  `digitalharmonyai.cloudflareaccess.com`).
- Two cloudflared tunnels, **locally-managed** (ingress in root-owned `/etc/cloudflared/config*.yml`)
  → tunnel **ingress is not addressable by the Cloudflare API** (see ingress carve-out).
- Doppler (`dhg-infra`) is the secrets manager.

## Verified MCP facts (`cloudflare/mcp`)

- Exposes the **entire** Cloudflare API incl. Zero Trust/Access, DNS, tunnels, Workers/R2/KV/D1. Auth:
  OAuth **or API token** (token path used). Code Mode: ON = 2 tools (`search`/`execute`); OFF = ~2,500
  typed tools. **v1 uses Code Mode ON** (2 tools; the token — not the tool surface — is the boundary).

## Architecture

```
You ──▶ cloudflare-ops SKILL (inline, user-level)
            │   classify op (read / routine write / destructive)
            │   destructive → show diff → one in-line confirm
            │
            └─▶ Cloudflare API MCP (Code Mode ON)
                  auth: WRITE-CAPABLE token via `doppler run`
                  executes reads + writes across all of scope C
                                      │
                  (ingress carve-out) └─▶ local tunnel ingress: NOT API-addressable
```

Two units: the **skill** (intent → op-classification + confirm gate + live ID resolution) and the
**official MCP** (full CRUD capability via the write token).

## Component 1 — `cloudflare-ops` skill

User-level (`~/.claude/skills/cloudflare-ops/`); spans both projects.

- **Op classification + confirm gate** per the table above.
- **Resolve-live:** never cache audience tags / app IDs / tunnel IDs — resolve from the API at call
  time. No concrete resource IDs baked into procedures.
- **Playbooks (decision procedures, not ID lists):** start with **`access-login <host> on|off`**;
  add more only the second time an intent recurs.
  - `access-login`: resolve the app gating `<host>` → compute desired policy state ("off" = the
    verified action that disables login; "on" = restore require-login) → it's destructive →
    show diff + **wildcard blast-radius note** → confirm → execute → verify via
    `curl -s -o /dev/null -w "%{http_code}" https://<host>` (`200` origin = off; `302` to
    `cloudflareaccess.com` = on).
- **Wildcard caveat (load-bearing honesty):** the single wildcard app means toggling `<host>`
  currently affects **all** `*.digitalharmonyai.com` siblings. The skill must surface this in the
  confirm. True per-host toggle requires restructuring into per-host apps (future).

## Component 2 — Cloudflare API MCP (write-capable)

- Official `cloudflare/mcp`, **Code Mode ON**.
- Launched via `doppler run --project dhg-infra --config <cfg> -- <mcp launch>`, injecting the
  **write-capable** token (so the token never lands in a file).
- **Token (Stephen mints):** one broad token — Account: Access Apps & Policies (Edit), Tunnel (Edit),
  Workers/Pages/R2/KV/D1 (Edit); Zone: DNS (Edit), Zone (Read). Stored in Doppler `dhg-infra`.

## Ingress carve-out (the one non-API piece)

Because the tunnels are **locally-managed**, editing tunnel **ingress** (`/etc/cloudflared/config*.yml`)
is not reachable via the API/token, and the harness can't sudo. Two ways to make it fit scope C —
**decide in the plan:**
1. **Migrate the tunnels to remotely-managed config** → ingress becomes an API call the write token
   already covers, and this carve-out disappears entirely. *Recommended* — keeps everything in one
   model. (One-time migration; config moves to Cloudflare.)
2. **Constrained root `cf-ingress` wrapper** + narrow NOPASSWD sudoers (allowlisted host→port,
   YAML-parse-not-sed, root-owned audit) — keeps config local but adds a privileged component.

Everything *except* local ingress is full CRUD via the token from day one.

## Security posture (per Stephen's accepted risk)

- **Accepted:** broad write token in an injectable agent. Trade for full capability on a single-user box.
- **Mitigations chosen:** one in-line confirm on destructive ops (with diff); Access-policy edits
  always confirm; **Cloudflare Audit Logs** are the authoritative record (all writes are API calls);
  **kill-switch** = rotate the token in Doppler + dashboard.
- **Not chosen (noted, available later if wanted):** out-of-band confirm, read-only default, split
  tokens.

## Failure modes / Definition of done

- **Idempotent:** re-running a write at desired state is a no-op.
- **Confirm fires:** a destructive op (e.g. Access-policy edit, DNS delete) shows a diff and requires
  confirmation before executing; a read or routine write does not.
- **Access round-trip:** `access-login docs off` → curl shows `200` origin → `access-login docs on` →
  curl shows `302` to cloudflareaccess.com. Restore path tested with equal rigor; if `on` fails after
  `off`, recovery is immediate (re-run converge).
- **Coverage smoke:** one successful read + one routine write + one (confirmed) destructive write
  across at least Access and DNS.
- **Kill-switch:** rotating the token revokes all agent Cloudflare power; documented runbook.

## Open items to resolve in the implementation plan

1. Exact Cloudflare **Access "off"/"on" policy action** under the wildcard app (Bypass/Everyone policy
   vs. action change) — verify against the live Access model.
2. Final **destructive-op classification** list per product (which exact API calls require confirm).
3. **Ingress carve-out** decision (remote-managed migration vs. `cf-ingress` wrapper).
4. Confirm the official MCP's token-auth launch command + Code Mode ON behavior in Claude Code.

## Version history

- **full-capability (this file), 2026-06-06** — scope C, write-capable token, Claude executes,
  one in-line confirm on destructive ops, Code Mode ON, ingress carve-out flagged. Per Stephen's
  correction that the scoped read-only design did not match intent.
- **`..._v2.md`** — rejected safe v1 (read-only + human-executed).
- **`..._v1.md`** — original 3-layer draft (daemon + broad token + Code Mode OFF).
