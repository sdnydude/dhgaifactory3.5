# Multica + Local LLM Integration Plan

**Created:** 2026-05-26
**Status:** Phase 1 ready
**Decision:** Not a /ship — infrastructure evaluation, no repo code changes

---

## Phase 1 — Trial Install (1 hour, zero risk)

### Prerequisites
- [ ] RTX 5090 installed in g700data1 (or use 5080 for initial test)
- [ ] Ollama running on g700data1

### Tasks
- [ ] **1.1** Pull Qwen3.6-27B: `ollama pull qwen3.6:27b` (~17GB download)
- [ ] **1.2** Verify VRAM usage: `nvidia-smi` while model is loaded — confirm it fits with headroom
- [ ] **1.3** Smoke test coding quality: ask it to read a real file from the repo and add type hints, write a test, refactor a function
- [ ] **1.4** Test tool calling: verify Qwen3.6-27B handles function call format reliably (not just chat)
- [ ] **1.5** Install OpenCode CLI: `brew install opencode` on g700data1
- [ ] **1.6** Configure OpenCode → Ollama: set provider to `http://localhost:11434/v1`, model to `qwen3.6:27b`
- [ ] **1.7** Verify OpenCode reads CLAUDE.md: run OpenCode against dhgaifactory3.5 repo, check if it follows project rules
- [ ] **1.8** Run one real task via OpenCode: pick a simple deferred item (e.g., "add type hints to export_service.py"), let it run end-to-end
- [ ] **1.9** Evaluate output: did it produce usable code? Did it need manual correction? How long did it take?

### Go/No-Go
- If 1.8 produces code that passes tests without major rework → proceed to Phase 2
- If tool calling is unreliable or output needs heavy editing → stop, revisit when models improve

---

## Phase 2 — Self-Host Multica (half day)

### Prerequisites
- [ ] Phase 1 passed go/no-go
- [ ] Docker running on g700data1

### Tasks
- [ ] **2.1** Clone Multica: `git clone https://github.com/multica-ai/multica.git`
- [ ] **2.2** Review docker-compose.yml — identify port conflicts (Postgres 5432 → remap to 5433 or 5436)
- [ ] **2.3** Create `.env` for Multica with JWT_SECRET, remap ports, set APP_ENV=production
- [ ] **2.4** Run `multica setup self-host` — bring up Multica server containers
- [ ] **2.5** Verify Multica web UI accessible at assigned port
- [ ] **2.6** Install Multica CLI on g700data1: `brew install multica-ai/tap/multica`
- [ ] **2.7** Run `multica login` and authenticate
- [ ] **2.8** Start daemon: `multica daemon start` — verify it detects Claude Code CLI on PATH
- [ ] **2.9** Verify daemon also detects OpenCode CLI on PATH
- [ ] **2.10** Check Settings → Runtimes in Multica web UI — g700data1 should appear as active runtime
- [ ] **2.11** Create first agent: "Claude" backed by Claude Code CLI
- [ ] **2.12** Create second agent: "CodeBot" backed by OpenCode CLI (→ Ollama → Qwen3.6-27B)
- [ ] **2.13** Create a test issue on the board, assign to CodeBot — verify it picks up, executes, reports
- [ ] **2.14** Create a test issue, assign to Claude — verify it picks up, executes, reports
- [ ] **2.15** Compare results: same task, both agents. Note quality difference and time difference.
- [ ] **2.16** Optionally expose Multica UI via Cloudflare tunnel (new subdomain in aifactory config)
- [ ] **2.17** Add Multica port to MEMORY.md port map

### Go/No-Go
- If both agents complete tasks and the board provides useful visibility → proceed to Phase 3
- If Multica daemon is unstable or agent execution is flaky at v0.3.x → pause, revisit at v0.5+

---

## Phase 3 — Mac as Second Runtime (only if needed)

### Prerequisites
- [ ] Phase 2 running and useful
- [ ] Need for parallel agent execution or larger model confirmed

### Tasks
- [ ] **3.1** Install LM Studio on Mac M3 Max (128GB)
- [ ] **3.2** Pull Qwen3-Coder-Next 80B MLX 4-bit via LM Studio (~45GB download)
- [ ] **3.3** Start LM Studio local server — verify OpenAI-compatible API at `http://localhost:1234/v1`
- [ ] **3.4** Smoke test: same coding task from Phase 1.8 against the 80B model — compare quality to 27B
- [ ] **3.5** Install Multica CLI on Mac: `brew install multica-ai/tap/multica`
- [ ] **3.6** Run `multica login` + `multica daemon start` on Mac
- [ ] **3.7** Install OpenCode on Mac, configure → LM Studio endpoint + qwen3-coder-next model
- [ ] **3.8** Verify Mac appears as second runtime in Multica Settings → Runtimes
- [ ] **3.9** Create agent "CodeBot-Mac" backed by OpenCode on Mac runtime
- [ ] **3.10** Test: assign issue to CodeBot-Mac, verify it executes on Mac hardware
- [ ] **3.11** Benchmark: time the same task on 5090 (27B) vs Mac (80B) — document quality vs speed tradeoff
- [ ] **3.12** Pull Qwen3-VL-30B-A3B MLX for Portage vision evaluation (separate from coding agents)

### Go/No-Go
- If Mac adds meaningful capability (better quality from 80B, or useful parallelism) → keep it
- If 27B on 5090 is "good enough" for everything → skip Mac runtime, use Mac for vision only

---

## Phase 4 — Production Split

### Prerequisites
- [ ] Phase 2 or 3 proven useful over 1+ weeks of real work

### Tasks
- [ ] **4.1** Define routing guidelines: which task types go to which agent
- [ ] **4.2** Document in CLAUDE.md: Multica section with agent names, model backing, intended workloads
- [ ] **4.3** Optionally create a Multica Squad: @BackendTeam with Claude as leader, CodeBot as member
- [ ] **4.4** Set up Autopilots for recurring tasks (e.g., weekly dependency audit, test coverage check)
- [ ] **4.5** Track cost savings: estimate Claude API spend avoided by routing routine work locally
- [ ] **4.6** Evaluate after 2 weeks: is the Multica workflow saving time, or is it overhead?
- [ ] **4.7** Update LLM strategy memory with production findings

### Go/No-Go
- If net positive on time and cost → make permanent
- If overhead exceeds benefit → simplify to just "local OpenCode for simple tasks, Claude Code for everything else" without Multica

---

## Model Reference (from research session 2026-05-26)

| Model | SWE-bench | Hardware | VRAM | Role |
|-------|-----------|----------|------|------|
| Qwen3.6-27B | 77.2% | 5090 (Ollama) | 17GB Q4 | Routine coding |
| Qwen3-Coder-Next 80B | ~70.6% | Mac M3 Max (MLX) | 45GB 4-bit | Heavy local (if needed) |
| Devstral Small 2 | 68% | Either | 14GB | Alternative/backup |
| Claude Sonnet 4.6 | 79.6% | Cloud | — | Complex architecture |
| Claude Opus 4.7 | 87.6% | Cloud | — | Hardest problems |
| Qwen3-VL-30B-A3B | N/A | Mac M3 Max (MLX) | 18GB | Portage vision (Phase 3+) |
