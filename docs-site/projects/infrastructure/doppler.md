---
sidebar_position: 2
title: Doppler — Secrets Management
---

# Doppler — Secrets Management

All secrets for Digital Harmony Group projects live in **Doppler**. No `.env` files
in notes, no copying keys between projects — one dashboard, one CLI, every server.

**Dashboard:** [secrets.digitalharmonyai.com](https://secrets.digitalharmonyai.com) (redirects to Doppler)
**Workspace:** `DigitalHarmonyai`

## How it works

Doppler Cloud is the single source of truth. Every server pulls secrets at runtime;
change a value in Doppler and the next time a service starts it gets the new value.

<img src="/img/infrastructure/doppler-architecture.svg" alt="DHG Doppler architecture: Doppler Cloud projects (portage, aifactory, dhg-infra shared, and 5 more) each with dev/stg/prd configs feeding secrets at runtime to g700data1 CLI, server 2 CLI, and CF Workers API" style={{maxWidth: '720px', width: '100%'}} />

## Projects

Each project is a Doppler **project**; shared keys used by more than one project live
in **`dhg-infra`** so they're referenced, never copied.

| Doppler project | What it covers |
|-----------------|----------------|
| **dhg-infra** | Shared keys used across projects — Cloudflare, tunnel creds, cross-project API tokens (e.g. the GitHub PAT) |
| **aifactory** | AI Factory 3.5 platform + all sub-services |
| **portage** | Inventory / multi-marketplace app (API, web, DB, AI providers) |
| **medkb** | Medical knowledge base |
| **dhg-transcribe** | Transcription pipeline |
| **dhg-audio** | Audio analysis agent |
| **dhg-cognitive** | Cognitive agent |
| **dhg-monitoring** | Grafana, Prometheus, observability |

(`example-project` is Doppler's bundled sample and can be ignored.) Run
`doppler projects` for the live list and `doppler secrets --project <name> --config <env>`
for current contents.

### Environments

Every project has three configs, mapping to standard environments:

| Config | Environment |
|--------|-------------|
| `dev` | Development |
| `stg` | Staging |
| `prd` | Production |

Right now most values are identical across environments. As projects move toward
production, the environments differentiate (separate DB passwords, separate keys).

## CLI setup

```bash
# Install
curl -Ls https://cli.doppler.com/install.sh | sh

# Authenticate (or use a service token for headless servers)
doppler login

# Bind the current directory to a project + config
doppler setup --project portage --config dev
```

Verify the active scope any time with `doppler configure`.

## Everyday workflows

### Start a service with secrets injected

`doppler run` injects every secret as an environment variable into the process — no
`.env` file required.

```bash
cd ~/DHG/portage
doppler run -- npm run dev:api
doppler run -- docker compose up -d
```

### See / get / set secrets

```bash
doppler secrets                          # list (names + truncated values)
doppler secrets get OPENAI_API_KEY --plain
doppler secrets set EBAY_CLIENT_ID=my-new-key
```

### Set a secret in a specific project / config

```bash
doppler secrets set MY_KEY=value --project aifactory --config dev
```

### Shared secrets

If a key is used by more than one project (an API key, a Cloudflare token), put it in
**`dhg-infra`** and reference it from there — don't duplicate it per project.

### "I changed a secret but the service doesn't see it"

`doppler run` injects at **startup**. A running process still holds the old values —
restart it:

```bash
doppler run -- docker compose restart portage-api
```

## The `.env` file

Each project still has a `.env`, but it is **generated from Doppler, not the reverse**:

<img src="/img/infrastructure/doppler-env-flow.svg" alt="The .env file is generated one-directionally from Doppler: Doppler (source of truth) → doppler secrets download → .env (local cache, auto-generated) → docker compose / npm run dev" style={{maxWidth: '380px', width: '100%'}} />

Edits to `.env` are lost on the next session — always change secrets in Doppler
(`doppler secrets set` or the dashboard).

When you need the file:

- **`doppler run -- <cmd>`** — does **not** need `.env`; injects directly.
- **`docker compose up` (without `doppler run`)** — reads `.env` via `env_file:`; needs the file.
- **IDE / editor tooling** — some tools read `.env` for autocomplete or tests.

## Claude Code integration

### Automatic — every session

In a Doppler-configured project directory, the **SessionStart hook** runs
`doppler secrets download` and rewrites `.env` with fresh values, so the local cache is
always current:

<img src="/img/infrastructure/doppler-session-sync.svg" alt="Claude Code SessionStart hook flow: Session starts → doppler-sync.sh → downloads secrets → writes .env" style={{maxWidth: '720px', width: '100%'}} />

### `/secrets` command

| Command | What it does |
|---------|--------------|
| `/secrets` | List all secrets (names + truncated values) |
| `/secrets get KEY` | Show full value of one secret |
| `/secrets set KEY=value` | Create / update a secret, auto-sync `.env` |
| `/secrets delete KEY` | Remove a secret (confirms first) |
| `/secrets sync` | Pull latest from Doppler → regenerate `.env` |
| `/secrets diff` | Show differences between `.env` and Doppler |
| `/secrets search term` | Find a key by name across all projects |
| `/secrets projects` | List all DHG Doppler projects |
| `/secrets switch project` | Point the current directory at another project |
| `/secrets env prd` | Switch the active environment |
| `/secrets open` | Open the Doppler dashboard |

### Shell aliases (`~/.bashrc`)

```bash
# Run any command with Doppler secrets injected
drun portage dev docker compose up -d
drun aifactory prd docker compose restart dhg-frontend

# Quick sync: pull latest secrets → .env
dsync
```

## Security practices

- **Rotate through Doppler**, never by editing files directly.
- **Never paste a secret into a chat, ticket, or commit.** If one is exposed, rotate it
  immediately and re-set the fresh value in Doppler.
- **Shared keys belong in `dhg-infra`**, referenced — not copied per project.
- **Restart services after a change** so `doppler run` re-injects the new value.

## Worked example: adding a shared GitHub PAT

A GitHub Personal Access Token used by the Claude Code `github` MCP plugin is a
cross-project credential, so it lives in `dhg-infra`:

```bash
# Store it (value piped in, never echoed back)
doppler secrets set GITHUB_PERSONAL_ACCESS_TOKEN \
  --project dhg-infra --config dev --silent <<< "github_pat_xxx"

# Verify it's present without printing the value
doppler secrets --project dhg-infra --config dev --only-names | grep GITHUB
```

The plugin reads it from the environment (`Bearer ${GITHUB_PERSONAL_ACCESS_TOKEN}`), so
expose it to Claude Code either by launching through Doppler
(`doppler run --project dhg-infra --config dev -- claude`) or by setting it in
`~/.claude/settings.local.json` under `env`.
