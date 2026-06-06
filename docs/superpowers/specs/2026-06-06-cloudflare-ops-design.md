# cloudflare-ops — Design Spec (full-capability, no deferrals)

**Date:** 2026-06-06
**Status:** Active design — pending spec review → implementation plan
**Author:** Claude (Opus 4.8) + Stephen Webber
**Reviewers:** security-auditor + systems-architect advisor subagents (two passes, 2026-06-06)

## Intent

Claude **directly reads, writes, and edits the entire Cloudflare setup** on request — **scope C,
full CRUD**: Zero Trust Access apps/policies, DNS, **tunnels including ingress**, Workers/Pages/
R2/KV/D1. Claude executes changes itself via a write-capable token. The motivating pain (toggling
Access login for a subdomain) is just one write Claude performs.

**Risk decision (Stephen's, explicit):** a write-capable token held by an LLM agent has a
prompt-injection blast radius. On this single-user dev server he accepts that for full capability.
Mitigations: **one in-line confirm + diff on destructive ops**, **Cloudflare Audit Logs** as the
authoritative record, **token-rotation kill-switch**. Nothing is deferred; every item below is decided.

## Confirmation model (core behavior)

| Op class | Examples | Behavior |
|---|---|---|
| **Read** | list/get anything | Auto |
| **Routine write** | create DNS record, create Access app, deploy/update Worker, write KV/R2 key, add a tunnel ingress route | Auto-execute, report what changed |
| **Destructive write** | edit/weaken an Access policy; delete or repoint a DNS record; delete an Access app; delete a Worker/Pages project; delete an R2 bucket / KV namespace / D1 database or bulk-delete data; delete/disable a tunnel; remove an ingress route | **One in-line confirm + before/after diff**, then execute |

All writes are **desired-state / idempotent** (read current → diff → converge). Access-policy edits are
always destructive (they can un-auth public services) and always confirm.

## Environment facts (verified)

- Server `g700data1` (10.0.0.251), user `swebber64`. Bash tool non-interactive (no PTY); `sudo -n`
  needs a password; `!`-paste can't do interactive auth.
- Wildcard Zero Trust Access app gates all `*.digitalharmonyai.com` (team
  `digitalharmonyai.cloudflareaccess.com`).
- Two cloudflared tunnels (`cloudflared.service` 30437aa6-…, `cloudflared-portage.service` 011e7e87-…),
  currently **locally-managed** (ingress in root-owned `/etc/cloudflared/config*.yml`). **Decision
  below migrates them to remote-managed** so ingress is API-controlled.
- Doppler (`dhg-infra`) is the secrets manager.

## Verified MCP facts (`cloudflare/mcp`)

Exposes the entire Cloudflare API incl. Zero Trust/Access, DNS, tunnels, Workers/R2/KV/D1. Auth: OAuth
**or API token** (token path used). **Code Mode ON** = 2 tools (`search`/`execute`); used here (the
write token, not the tool surface, is the boundary).

## Architecture

```
You ──▶ cloudflare-ops SKILL (inline, user-level)
            │  classify op (read / routine / destructive)
            │  destructive → diff → one in-line confirm
            │
            └─▶ Cloudflare API MCP (Code Mode ON)
                  auth: WRITE-CAPABLE token via `doppler run`
                  executes ALL of scope C — incl. tunnel ingress
                  (after tunnels are remote-managed)
```

## Decisions (all pinned — no open items)

**D1 — Form factor:** inline user-level skill (`~/.claude/skills/cloudflare-ops/`). Cloudflare ops is
*doing* (short, stateful, interactive); skill, not subagent.

**D2 — MCP + token:** official `cloudflare/mcp`, **Code Mode ON**, launched
`doppler run --project dhg-infra --config <cfg> -- <official cloudflare/mcp launch>` so the token is
injected at runtime. **Token (Stephen mints):** one broad token — Account: Access Apps & Policies
(Edit), Tunnel + Tunnel Configuration (Edit), Workers/Pages/R2/KV/D1 (Edit); Zone: DNS (Edit), Zone
(Read). Stored in Doppler `dhg-infra`.

**D3 — Tunnel ingress = migrate to remote-managed.** Both tunnels are converted to Cloudflare
dashboard-managed configuration. After migration, the ingress route list lives in Cloudflare and is
edited via the API/token like everything else — **no root, no sudo, no wrapper, no local-file edits.**
This is a one-time migration performed during implementation (move each tunnel's ingress rules from
`config*.yml` into the remote configuration, then run the tunnel with remote config). The local
`config*.yml` is retired to credentials/`tunnel:` only.

**D4 — Access login on/off mechanism** (verified this session, see
`memory/reference_cloudflare_access_wildcard.md`): "off" = set the gating app's identity policy to
**Bypass / Everyone** (reusable policies are edited at Access controls → Policies; the skill resolves
and calls the exact API endpoint live). "on" = restore the require-login policy (`Allow` with the
company-email include). The skill resolves the app gating `<host>` live and converges to desired state.
**Wildcard reality (stated, not deferred):** with the current single wildcard app, toggling one host
changes auth for **all** `*.digitalharmonyai.com` siblings; the confirm surfaces this blast radius
every time. (Stephen's accepted behavior — he toggles the wildcard intentionally.)

**D5 — Resolve-live:** the skill never caches audience tags / app IDs / tunnel IDs; it resolves them
from the API at call time. No resource IDs baked into procedures.

**D6 — Playbooks:** ship one — `access-login <host> on|off` (D4). Additional playbooks are added the
second time an intent recurs (this is a build convention, not a deferred feature).

**D7 — Audit + kill-switch:** writes are API calls, captured in **Cloudflare Audit Logs**
(authoritative). Kill-switch = rotate the token in Doppler + dashboard.

## Definition of done

- **Idempotent:** re-running any write at desired state is a no-op.
- **Confirm fires correctly:** a destructive op shows a diff and requires confirmation; reads and
  routine writes do not.
- **Access round-trip:** `access-login docs off` → `curl -s -o /dev/null -w "%{http_code}"
  https://docs.digitalharmonyai.com` returns `200` (origin); `access-login docs on` → returns `302`
  to `cloudflareaccess.com`. The `on` restore is verified with equal rigor (no open public window).
- **Ingress via API:** after D3, create + remove a tunnel ingress route through the skill (no local
  file edit, no sudo) and confirm the hostname resolves to the mapped local service.
- **Coverage smoke:** one read + one routine write + one confirmed destructive write across Access,
  DNS, and a dev-platform product.
- **Kill-switch:** rotating the token removes all agent Cloudflare power.

## Implementation phases (every piece built — nothing parked)

1. Mint + store the write token (D2); add the MCP server (Code Mode ON) via `doppler run`.
2. Build the skill: op classification + confirm gate + resolve-live (D1, D5).
3. `access-login` playbook end-to-end with the curl verification (D4, D6).
4. Migrate both tunnels to remote-managed config (D3); wire ingress create/remove through the skill.
5. Verify full DoD (incl. ingress round-trip, destructive-confirm, kill-switch).

## Version history

- **full-capability / no-deferrals (this file), 2026-06-06** — scope C fully decided: write token,
  Claude executes, one confirm on destructive ops, Code Mode ON, **ingress resolved via remote-managed
  migration (D3)**, Access on/off mechanism pinned (D4). Removed all "open items"/"out of scope"
  deferrals per Stephen's directive.
- `..._v3.md` — same capability but with ingress + open items deferred to the plan (rejected: no deferrals).
- `..._v2.md` — over-scoped-down read-only / human-executed v1 (rejected: didn't deliver capability).
- `..._v1.md` — original 3-layer draft (daemon + broad token + Code Mode OFF).
