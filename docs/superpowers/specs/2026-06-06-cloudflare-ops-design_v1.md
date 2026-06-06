# cloudflare-ops — Design Spec

**Date:** 2026-06-06
**Status:** Approved design (pending spec review → implementation plan)
**Author:** Claude (Opus 4.8) + Stephen Webber
**Reviewers:** security-auditor + systems-architect advisor subagents (2026-06-06)

## Problem

Stephen needs to read, write, and edit his Cloudflare setup via natural-language
requests to Claude. The recurring concrete pain: toggling Cloudflare Zero Trust
**Access** login on/off for a subdomain (e.g. `docs.digitalharmonyai.com`) currently
has **no tooling** — it gets manually re-derived in the dashboard every session, and the
session bash harness cannot perform it (no reachable API token; `sudo` unavailable
non-interactively; the `!`-paste fallback fails because the non-interactive shell has no
TTY for a sudo password prompt).

Scope chosen by Stephen: **C — everything** (Zero Trust Access apps/policies, DNS,
tunnel routes, Workers/Pages/R2/KV/D1).

## Environment facts (verified this session)

- Single Ubuntu dev server `g700data1` (10.0.0.251), single user `swebber64`.
- Claude Code runs as `swebber64` in a non-interactive bash harness. **Verified:**
  `sudo -n true` → "a password is required" (no NOPASSWD rule exists; sudo itself runs).
- Two cloudflared tunnels: `cloudflared.service` (aifactory, tunnel `30437aa6-…`) and
  `cloudflared-portage.service` (portage, tunnel `011e7e87-…`). Root-owned configs at
  `/etc/cloudflared/config.yml` and `/etc/cloudflared/config-portage.yml`.
- All `*.digitalharmonyai.com` subdomains are gated by **one wildcard Zero Trust Access
  application** (team `digitalharmonyai.cloudflareaccess.com`; the docs-gating app's
  audience tag observed as `a1caece9a2d7257ca872da66d83d2b755fe6d35240f138666f62d7af7c103f50`).
- Doppler is the secrets manager (installed, authenticated; `dhg-infra` project).

## Verified capability of the official Cloudflare MCP (`cloudflare/mcp`)

- Exposes the **entire** Cloudflare API (~2,500 endpoints) across DNS, Workers, R2,
  **Zero Trust** (incl. Access, Gateway), and every other product. Access app/policy
  create/update/delete is reachable (via the generic `execute()`/`cloudflare.request()`
  passthrough — not a dedicated typed Access tool).
- Auth: **both OAuth and API token** ("for CI/CD or automation, create a Cloudflare API
  token … pass it as a bearer token"). The API-token path is what we use.
- **"Code Mode" toggle:** ON = 2 tools (`search` + `execute`, arbitrary JS). OFF = ~2,500
  individual typed endpoint tools. Turning Code Mode **OFF** removes the single
  arbitrary-`execute()` surface.

## Design decisions (and reversals from the first draft)

| Decision | Choice | Why |
|---|---|---|
| Form factor | **Inline skill** (not subagent) | Cloudflare ops is *doing* — short, stateful, interactive, needs main-thread confirms. Subagents are for *understanding*. |
| API access | **Official `cloudflare/mcp`** + thin DHG skill | Don't reinvent 2,500 endpoints; skill adds judgment + local facts. |
| Token (REVERSED from "one broad token") | **Read-only by default**, scoped to products used; **write capability gated** | Consumer is a prompt-injectable LLM. Enforcement must be at the credential, not skill prose — the MCP's raw `execute()` bypasses any prose guardrail. |
| Crown-jewel writes (Access policy, DNS) | **Out-of-band confirm** (not in-band) | In-band "confirm?" is injection-bypassable (the attacker controls the same channel). |
| Resource map | **Resolve IDs live from the API; do NOT cache a static table** | A cached table of audience tags/tunnel IDs rots and makes the agent confidently wrong (documented read-side failure mode). |
| Tunnel ingress (root-owned) (REVERSED from daemon, then from `!`-paste) | **Constrained root wrapper + one narrow NOPASSWD sudoers entry** | Daemon watching a user-writable dir *launders* privilege (escalation surface for injected Claude). `!`-paste fails (no TTY). Constrained wrapper confines *what* can change and works non-interactively via `sudo -n`. |
| Audit | **Cloudflare's own Audit Logs** as authoritative | A `swebber64`-writable local log is forgeable by the actor it audits. |
| Daemon | **Cut entirely** | Standing root service for a monthly op; upside-down YAGNI; replaced by the wrapper. |

## Architecture

```
You ──▶ DHG cloudflare-ops SKILL (intent → vetted procedure; guardrails)
            │
            ├─▶ Cloudflare API MCP (official cloudflare/mcp, Code Mode OFF)
            │     auth: API token via `doppler run`; READ-ONLY by default
            │     covers Access / DNS / tunnels-via-API / Workers / R2 / KV / D1
            │
            └─▶ tunnel INGRESS only ──▶ sudo -n /usr/local/bin/cf-ingress <verb> <args>
                                         (root-owned wrapper, host/port allowlist,
                                          validate + reload; one NOPASSWD sudoers line)
```

Three units, each independently understandable:
1. **Skill** — encodes *our* intents + guardrails; resolves resource IDs live.
2. **Official MCP** — raw API capability, constrained by token scope.
3. **`cf-ingress` wrapper** — the only privileged piece, confined to allowlisted ingress edits.

## Component 1 — `cloudflare-ops` skill

Installs at **user level** (`~/.claude/skills/cloudflare-ops/`) since the Cloudflare setup
spans both projects (aifactory + portage tunnels, the shared zone).

Contents:
- **Guardrails (stable, low-rot):**
  - Read-only by default. Reads need no confirm.
  - Writes require the write-capable credential path (see token model) AND, for
    crown-jewel ops (Access policy, DNS), an out-of-band confirm.
  - Every write: read current state → show diff → converge to **desired state**
    (idempotent; safe to re-run). No blind relative toggles.
- **Resolve-live instruction:** never cache audience tags / tunnel IDs / app IDs;
  resolve them from the API at call time (list Access apps, match the subdomain). Only
  genuinely stable, non-derivable facts (account ID, team/org name) may be noted, and
  even those are verify-on-use.
- **One playbook to start:** `access-login <host> on|off`, written as a desired-state
  procedure (resolve the app gating `<host>` by matching its domain/aud → set policy
  to require-login or bypass/allow → verify via the public-redirect curl check). Add
  further playbooks only the *second* time an intent recurs — never speculatively.

## Component 2 — Cloudflare API MCP wiring

- Server: official `cloudflare/mcp`, **Code Mode OFF** (typed endpoint tools, no raw
  arbitrary `execute()`).
- Auth: API token injected at launch via `doppler run --project dhg-infra --config <cfg>
  -- <mcp launch>` so the token never lands in a config file.
- **Token model (Stephen mints in dashboard):**
  - **Default token = READ-ONLY**, scoped to the products in use (Access read, DNS read,
    Tunnel read, Workers/R2/KV/D1 read). This is the always-available credential.
  - **Write capability** is provisioned separately and is NOT freely available to the
    agent. Crown-jewel writes (Access policy, DNS) require an out-of-band human confirm
    before the write-scoped path is used.
  - (Exact split — one read token + one gated write token, vs. scoped-per-product — is a
    plan-level detail. Verify Cloudflare's per-resource / per-Access-app token granularity
    during planning.)
- Kill-switch: rotating the token in Doppler + Cloudflare dashboard instantly revokes
  the agent's Cloudflare power. Document this runbook.

## Component 3 — `cf-ingress` root wrapper (the privileged 5%)

- `/usr/local/bin/cf-ingress`, **root-owned, mode 0755**, ~20 reviewable lines.
- **Fixed argument grammar**, e.g. `cf-ingress expose <host> <port>` /
  `cf-ingress unexpose <host>`.
- **Allowlist baked into the script** (root-owned): permitted hostnames and permitted
  loopback ports. Anything off-allowlist is rejected. The request *cannot* express
  "repoint host Y to attacker Z" or "expose arbitrary new service."
- Steps: validate args against allowlist → edit the correct `/etc/cloudflared/config*.yml`
  (atomic write, preserve the catch-all 404) → `cloudflared tunnel ingress validate` →
  `systemctl reload` the matching service.
- One sudoers drop-in: `swebber64 ALL=(root) NOPASSWD: /usr/local/bin/cf-ingress`.
- Skill invokes `sudo -n /usr/local/bin/cf-ingress …` (no TTY/password needed under
  NOPASSWD).
- **One-time setup is Stephen's** (install script + sudoers drop-in; both need root).

## Security posture (from adversarial review)

- **Enforcement is the credential, not prose.** Read-only default token makes any
  talked-into write physically impossible; Code-Mode-OFF removes the arbitrary-execute
  surface.
- **Crown jewels gated out-of-band.** Editing the wildcard Access policy can un-auth the
  entire public surface; DNS edits can repoint subdomains. These never proceed on an
  in-band confirm.
- **Ingress privilege confined** to an allowlisted, fixed-grammar root wrapper — not a
  watcher daemon, not a user-writable config.
- **Audit = Cloudflare Audit Logs** (authoritative; not the agent self-reporting into a
  forgeable local file).
- **Kill-switch = token rotation** (documented runbook).

## Failure modes / "done"

- **Idempotency:** all writes are desired-state; re-running is a no-op.
- **Diff requires read-current:** the write path always fetches current state first.
- **Ingress reload failure:** wrapper validates before reload; on validate failure it does
  not write/reload (tunnel stays up).
- **Definition of done:** end-to-end `access-login docs off` → verified by the public
  redirect curl (`curl -s -o /dev/null -w "%{http_code}" https://docs.digitalharmonyai.com`
  → 200 origin, no 302 to cloudflareaccess.com) → `access-login docs on` restores the gate;
  one `cf-ingress` expose/unexpose round-trip on an allowlisted host; read ops across
  Access/DNS/Workers succeed with the read-only token.

## Out of scope / deferred

- Per-product / per-Access-app token granularity beyond read-vs-write split (verify and
  decide in plan).
- Additional playbooks beyond `access-login` (add on second recurrence).
- Streaming audit to Loki (Cloudflare Audit Logs suffice initially).
- Splitting the wildcard Access app so data-bearing hosts don't share fate (separate
  infra change; noted by review, not part of this skill).

## Prerequisites (Stephen, one-time)

1. Mint Cloudflare API token(s) per the token model; store in Doppler `dhg-infra`.
2. Install `/usr/local/bin/cf-ingress` (root) + the NOPASSWD sudoers drop-in.
3. Decide the out-of-band confirm channel for crown-jewel writes (push/TOTP/SMS).
