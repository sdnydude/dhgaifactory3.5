# cloudflare-ops — Design Spec (v1)

**Date:** 2026-06-06
**Status:** Revised v1 — pending spec review → implementation plan
**Author:** Claude (Opus 4.8) + Stephen Webber
**Reviewers:** security-auditor + systems-architect advisor subagents (two passes, 2026-06-06)
**Supersedes:** pre-revision draft saved at `2026-06-06-cloudflare-ops-design_v1.md` (the 3-layer
design with daemon + broad token + Code-Mode-OFF). This file is the revised, scoped-down v1.

## Problem

Stephen needs to read, write, and edit his Cloudflare setup via natural-language requests to
Claude. The recurring concrete pain: toggling Cloudflare Zero Trust **Access** login on/off for a
subdomain (e.g. `docs.digitalharmonyai.com`) has **no tooling** today — it gets re-derived in the
dashboard every session, and the session bash harness cannot perform it (no reachable API token;
no interactive TTY for sudo/auth — verified).

## What changed from the draft (and why)

Two adversarial review passes drove four reversals. v1 is deliberately small.

| Draft | v1 | Why |
|---|---|---|
| One broad read+write token | **Read-only token only** in the agent's reach | A prompt-injectable agent that can `doppler secrets get` a write token has standing write power. The only real boundary is: the agent never holds write capability. |
| Agent auto-executes writes | **Agent prepares, human executes** writes | Writes need a real TTY + creds the harness lacks; Anthropic's own docs recommend "have Claude output the command so you run it in the terminal." Confirmed: Apple Terminal SSH into g700data1 is a real PTY where sudo/creds work. |
| Code Mode OFF (~2,500 tools) | **Code Mode ON (2 tools)** | ~2,500 tools is unworkable in Claude Code and taxes every session; ToolSearch would make the security benefit moot anyway. Enforcement is the **read-only token**, not the tool surface. |
| Root daemon, then `cf-ingress` wrapper | **Ingress deferred out of v1** | The recurring pain is Access, not tunnel ingress. No daemon, no wrapper, no sudoers, no root setup in v1. |

## v1 scope

- **Reads:** everything the read-only token permits (Access apps/policies, DNS, tunnels,
  Workers/R2/KV/D1) via the official MCP — fully automated.
- **Writes:** exactly one playbook — `access-login <host> on|off` — **agent-prepared,
  human-executed**.
- **Deferred:** DNS writes, dev-platform writes, and all tunnel-ingress editing (the `cf-ingress`
  wrapper / remote-managed-tunnel migration is a separate later decision).

## Environment facts (verified this session)

- Single Ubuntu server `g700data1` (10.0.0.251), user `swebber64`. Claude's Bash tool runs
  non-interactively (no PTY). **Verified:** `sudo -n` → "a password is required"; the `!`-paste
  also fails for interactive auth (no TTY).
- Apple Terminal (and an SSH session from it into g700data1) **is** a real interactive PTY — this
  is where human-executed writes run.
- Wildcard Zero Trust Access app gates all `*.digitalharmonyai.com` (team
  `digitalharmonyai.cloudflareaccess.com`). Two cloudflared tunnels, root-owned local configs
  (relevant only to the deferred ingress work).
- Doppler is the secrets manager (`dhg-infra`).

## Verified MCP facts (`cloudflare/mcp`)

- Exposes the entire Cloudflare API incl. **Zero Trust / Access** (Access writes reachable via the
  generic `execute()`/`cloudflare.request()` passthrough). Auth: **OAuth or API token** (token path
  used here). **Code Mode toggle:** ON = 2 tools (`search`/`execute`); OFF = ~2,500 typed tools.

## Architecture (v1)

```
You ──▶ cloudflare-ops SKILL (inline, user-level)
            │
            ├─ READS  ─▶ Cloudflare API MCP (Code Mode ON) ──▶ Cloudflare API
            │             auth: READ-ONLY token via `doppler run`
            │
            └─ WRITE (access-login) ─▶ resolve current state (read-only MCP)
                                       → compute desired state
                                       → EMIT exact command + before/after diff
                                       → YOU run it in Apple Terminal (real PTY)
```

Two units: the **skill** (intent → resolved read calls / prepared write commands) and the
**official MCP** (read-only capability). No daemon, no wrapper, no standing write power anywhere.

## Component 1 — `cloudflare-ops` skill

Installs at **user level** (`~/.claude/skills/cloudflare-ops/`); the setup spans both projects.

- **Guardrails:**
  - Reads are free (read-only token; nothing to gate).
  - Writes are **never executed by the agent**. The skill's write path ends at producing a vetted
    command + a before/after diff for the human to run.
  - All writes are **desired-state / idempotent** (read current → diff → converge), never blind flips.
- **Resolve-live:** never cache audience tags / app IDs / tunnel IDs — resolve from the API at call
  time. **No concrete resource IDs in the playbook body** (illustrative IDs belong in prose, not the
  procedure). Only stable, non-derivable facts (account ID, team name) may be noted, verify-on-use.
- **One playbook — `access-login <host> on|off`:**
  1. Resolve the Access application gating `<host>` (match by domain).
  2. **Blast-radius check (load-bearing):** if the gating app is the **wildcard**
     `*.digitalharmonyai.com` (it currently is), surface explicitly that toggling it affects
     **every** sibling subdomain — true per-host toggle is *not possible* without restructuring the
     Access apps (out of v1 scope; noted below). Proceed only on explicit acknowledgement.
  3. Compute desired state ("off" = the verified policy action that disables login — **verify the
     exact mechanism during planning**: Bypass/Everyone policy vs. policy action change vs. app
     deletion; "on" = restore the original require-login policy).
  4. **Emit** the exact command + before/after diff for the human to run (see write-execution model).
  5. After the human runs it, **verify** via the public redirect check:
     `curl -s -o /dev/null -w "%{http_code}" https://<host>` → `200` (origin, login off) vs `302`
     to `cloudflareaccess.com` (login on).

## Component 2 — Cloudflare API MCP (read-only)

- Official `cloudflare/mcp`, **Code Mode ON** (2 tools).
- Launched via `doppler run --project dhg-infra --config <agent-cfg> -- <mcp launch>`, injecting a
  **read-only** token. (Env injection is not a confidentiality boundary against a same-UID agent —
  acceptable here precisely because the token is read-only.)
- **Verify during planning:** that Cloudflare offers a genuinely read-only token scope covering the
  Access/DNS/tunnel reads we need (the enforcement spine depends on this being real).

## Write-execution model (the v1 core)

- The **write token** (Access edit; later DNS edit) lives **only** in a place the agent's harness
  cannot read — a separate Doppler config used solely from Stephen's interactive shell, or supplied
  ad hoc at run time. It is **never** in the MCP/agent environment.
- For a write, the skill emits a self-contained command Stephen pastes into his Apple Terminal SSH
  session into g700data1 — e.g. a `doppler run --config <write-cfg> -- curl …` against the Cloudflare
  API that converges the Access policy to the desired state — accompanied by the before/after diff so
  he sees exactly what changes before running it.
- Because the human runs the actual API write, it lands in **Cloudflare's own Audit Logs**
  (authoritative; the agent never self-reports into a forgeable local file).

## Security posture (v1)

- **No standing write power in the agent.** Read-only token + human-executed writes closes the
  central injection hole (no reachable write token to steal).
- **Code Mode ON is safe** because the read-only token makes `execute()` writes impossible; the tool
  surface is not the control.
- **Crown-jewel awareness:** `access-login` is treated as crown-jewel — the wildcard blast-radius
  check is mandatory before emitting the command.
- **Kill-switch:** rotate the read-only token (Doppler + dashboard) to cut the agent's read access;
  the write token, being human-only, is unaffected by agent compromise.

## Failure modes / Definition of done

- **Idempotent:** re-running `access-login <host> off` when already off is a no-op (desired-state).
- **Read fails closed (negative test, required):** an attempted *write* through the default
  read-only MCP token must be **rejected by Cloudflare** — proves enforcement is the credential.
- **Access round-trip:** `access-login docs off` (human-executed) → curl check shows `200` origin →
  `access-login docs on` → curl check shows `302` to cloudflareaccess.com. The restore (`on`) path is
  tested with equal rigor; if `on` ever fails after `off`, the prepared command must include the
  exact revert so there is no open public-exposure window.
- **Reads:** read queries across Access/DNS succeed with the read-only token.

## Open items to resolve in the implementation plan

1. **Exact Access "off"/"on" mechanism** under the current wildcard app (Bypass policy vs. action
   change vs. per-host restructuring) — verify against the live Cloudflare Access model.
2. **Read-only token scope** actually covers needed reads (verify Cloudflare token scopes).
3. The precise **emitted write command** form (`doppler run -- curl …` shape, where the write token
   lives).

## Out of scope (v1) / future

- DNS writes and dev-platform (Workers/R2/KV/D1) writes — add when a real need recurs.
- **Tunnel ingress editing** — deferred entirely. Future options: a constrained root `cf-ingress`
  wrapper + narrow NOPASSWD sudoers, OR migrating the tunnels to **remotely-managed** config (makes
  ingress an API call, removes all local-root needs). Decide later.
- **True per-host Access login** (so `docs` can be toggled without affecting siblings) — requires
  restructuring the single wildcard app into per-host apps; separate infra decision.

## Prerequisites (Stephen, one-time)

1. Mint a **read-only** Cloudflare API token; store in the agent-reachable Doppler config.
2. Mint a **write** token (Access edit) and keep it in a config reachable **only** from your
   interactive shell — never the agent's.
3. Add the official `cloudflare/mcp` server to Claude settings, launched via `doppler run` with the
   read-only token, Code Mode ON.

## Version history

- **v1 (this file), 2026-06-06** — scoped-down after two advisor passes: read-only token, agent-
  prepares/human-executes writes, Code Mode ON, ingress deferred, single `access-login` playbook.
- **draft, 2026-06-06** — `..._v1.md` backup: 3-layer design (MCP + skill + root daemon), one broad
  token, Code Mode OFF. Reversed per security + architecture review.
