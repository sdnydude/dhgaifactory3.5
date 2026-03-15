# Claude Code Plugins — Tactical User Guide

**27 plugins | 35 commands | 32 agents | 8 hooks | 6 MCP servers**

---

## Quick Reference: When to Use What

| I want to... | Use |
|---|---|
| Plan a multi-step feature | `/plan` or `/superpowers:writing-plans` |
| Brainstorm ideas | `/superpowers:brainstorming` |
| Execute a plan with agents | `/superpowers:executing-plans` or `/superpowers:subagent-driven-development` |
| Build a feature end-to-end | `/feature-dev` |
| Debug a failing test/bug | `/superpowers:systematic-debugging` |
| Write tests first, then code | `/superpowers:test-driven-development` |
| Review my code before commit | `/code-review` or `/review` |
| Deep PR review with specialists | `/review-pr` (pr-review-toolkit) |
| Simplify messy code | `/simplify` |
| Commit + push + PR in one shot | `/commit-push-pr` |
| Just commit with a good message | `/commit` |
| Clean up stale git branches | `/clean_gone` |
| Create a beautiful UI | `/frontend-design` |
| Create an interactive prototype | `/playground` |
| Generate tests for my code | `/test-gen` |
| Generate API docs | `/docs-gen` |
| Run a security audit | `/audit` |
| Check for vulnerabilities | `/vulnerability-scan` |
| Validate compliance (HIPAA, SOC2) | `/compliance-check` |
| Profile performance | `/profile` |
| Load test an endpoint | `/benchmark` |
| Check system health | `/health-check` |
| Validate before deploying | `/deploy-validate` |
| Assess tech debt | `/debt-analysis` |
| Assess codebase health | `/code-health` |
| Handle a production incident | `/incident-response` |
| Update CLAUDE.md with learnings | `/revise-claude-md` |
| Create a handoff doc for next session | `/handoff-create` or `/whats-next` |
| Track TODOs | `/todo-add`, `/todo-check` |
| Run a recurring check | `/loop 5m /health-check` |
| Create a new plugin | `/create-plugin` |
| Create a new skill | `/skill-creator` |
| Create a new Agent SDK app | `/new-sdk-app` |
| Prevent bad behaviors with hooks | `/hookify` |
| Get library docs in context | Use context7 MCP (automatic) |
| Train an ML model | `/hugging-face-model-trainer` |
| Build a Gradio demo | `/huggingface-gradio` |
| Query PostHog analytics | `/posthog:query` |

---

## Plugin Deep Dives

### 1. Superpowers (the meta-skill library)

The backbone. Provides structured workflows that chain together. Skills are triggered automatically when relevant, but you can invoke them directly.

| Skill | When it fires | What it does |
|---|---|---|
| `brainstorming` | Before any creative work | Structured ideation with constraints, tradeoffs, and decisions |
| `writing-plans` | Before multi-step implementation | Creates detailed plans with phases, files, and verification steps |
| `executing-plans` | When you have a written plan | Executes plan step-by-step with review gates |
| `test-driven-development` | Before writing implementation | RED-GREEN-REFACTOR cycle |
| `systematic-debugging` | When encountering bugs | Hypothesis-driven debugging with isolation |
| `dispatching-parallel-agents` | 2+ independent tasks | Launches parallel subagents for speed |
| `subagent-driven-development` | Independent implementation tasks | Executes plan tasks via isolated agents |
| `using-git-worktrees` | Feature work needing isolation | Isolates work in git worktrees |
| `requesting-code-review` | After completing a feature | Triggers thorough review before merge |
| `receiving-code-review` | When review feedback arrives | Structured approach to addressing feedback |
| `finishing-a-development-branch` | All tests pass, ready to merge | Decides merge strategy (squash, rebase, merge) |
| `verification-before-completion` | Before claiming "done" | Final verification that everything works |
| `writing-skills` | Creating/editing skills | Skill authoring best practices |

### 2. Feature Dev (guided feature building)

**Command:** `/feature-dev`

7-phase workflow:
1. **Discovery** — Understand what you're building
2. **Codebase exploration** — `code-explorer` agent maps the relevant code
3. **Clarifying questions** — Asks what's ambiguous
4. **Architecture design** — `code-architect` agent proposes approaches
5. **Implementation** — Builds it
6. **Quality review** — `code-reviewer` agent checks the work
7. **Summary** — Documents what was built

### 3. Code Review (PR-level)

**Command:** `/code-review`

Runs 4 parallel agents against your diff:
- 2x CLAUDE.md compliance checkers
- 1x Bug/logic error detector
- 1x Historical context analyzer

Only surfaces findings with **>=80% confidence** to avoid false positives.

### 4. PR Review Toolkit (deep specialist review)

**Command:** `/review-pr`

6 specialized agents you can invoke individually or together:

| Agent | Focus |
|---|---|
| `code-reviewer` | General quality, project guidelines |
| `comment-analyzer` | Comment accuracy and maintainability |
| `pr-test-analyzer` | Test coverage gaps |
| `silent-failure-hunter` | Swallowed errors, bad fallbacks |
| `type-design-analyzer` | Type invariants and encapsulation |
| `code-simplifier` | Unnecessary complexity |

### 5. Frontend Design

**Command:** `/frontend-design`

Generates distinctive, production-grade UIs. Avoids generic "AI-generated" aesthetics. Makes bold choices on typography, color, and animation.

### 6. Commit Commands

| Command | What it does |
|---|---|
| `/commit` | Auto-generates commit message from diff, creates commit |
| `/commit-push-pr` | Commit + push + create GitHub PR with summary and test plan |
| `/clean_gone` | Deletes local branches whose remotes are gone |

### 7. Hookify (behavior prevention)

**Commands:** `/hookify`, `/hookify:list`, `/hookify:configure`

Analyzes your conversation for mistakes Claude made, then creates hooks (bash scripts that run before/after tool calls) to prevent them in future sessions.

Example: If Claude keeps running `rm -rf` without asking, `/hookify` creates a pre-tool hook that blocks it.

### 8. Playground

**Command:** `/playground`

Creates single-file interactive HTML explorers. Templates:
- **design-playground** — Visual design decisions with live controls
- **data-explorer** — SQL/API/regex building with live preview
- **concept-map** — Learning and exploration
- **document-critique** — Document review workflow

### 9. Ralph Loop

**Command:** `/ralph-loop "<prompt>" --max-iterations 5`

Self-referential development loop. Claude runs your prompt, checks the result, then runs it again with feedback. Useful for:
- Iterative refinement tasks
- Tasks with clear success criteria
- Greenfield projects with automatic verification

Cancel with `/cancel-ralph`.

### 10. Planning with Files

**Commands:** `/plan`, `/status`

Creates 3 persistent files:
- `task_plan.md` — Phases, tasks, decisions
- `findings.md` — Research notes
- `progress.md` — What's done, what's blocked

Survives `/clear` and session restarts.

### 11. CLAUDE.md Management

| Command | What it does |
|---|---|
| `/revise-claude-md` | Captures learnings from current session into CLAUDE.md |
| `claude-md-improver` (skill) | Audits CLAUDE.md against actual codebase state |

### 12. Plugin Dev Toolkit

**Command:** `/create-plugin`

8-phase guided plugin creation. Also provides skills for building individual components:
- `hook-development` — Event-driven hooks
- `mcp-integration` — MCP server integration
- `skill-development` — Skill authoring
- `agent-development` — Agent creation
- `command-development` — Slash commands

### 13. Agent SDK Dev

**Command:** `/new-sdk-app [name]`

Scaffolds a Claude Agent SDK app (Python or TypeScript). Agents verify the app follows SDK best practices.

### 14. Skill Creator

Creates, improves, and benchmarks skills. Use when you want to add a reusable capability to Claude Code.

### 15. Claude Code Setup

**Skill:** `claude-automation-recommender`

Analyzes your codebase and recommends tailored automations — which hooks, skills, MCP servers, and subagents would help most.

---

## MCP Servers (6)

| Server | Source | Purpose |
|---|---|---|
| context7 | Plugin | Fetches up-to-date library docs on demand |
| playwright | Plugin | Browser automation (navigate, click, fill, screenshot) |
| github | Plugin | GitHub API integration |
| greptile | Plugin | Enhanced code search |
| gitlab | Plugin | GitLab API integration |
| posthog | Plugin | PostHog analytics queries |

---

## Agents (32)

Available via the Agent tool. Key ones:

| Agent | Plugin | Use for |
|---|---|---|
| `code-explorer` | feature-dev | Deep codebase analysis |
| `code-architect` | feature-dev | Architecture design |
| `code-reviewer` | feature-dev, pr-review-toolkit | Code quality review |
| `comment-analyzer` | pr-review-toolkit | Comment accuracy |
| `pr-test-analyzer` | pr-review-toolkit | Test coverage |
| `silent-failure-hunter` | pr-review-toolkit | Error handling gaps |
| `type-design-analyzer` | pr-review-toolkit | Type design quality |
| `code-simplifier` | code-simplifier | Simplify code |
| `agent-sdk-verifier-py` | agent-sdk-dev | Verify Python SDK app |
| `agent-sdk-verifier-ts` | agent-sdk-dev | Verify TypeScript SDK app |
| `conversation-analyzer` | hookify | Find behaviors to prevent |
| `agent-creator` | plugin-dev | Create new agents |
| `plugin-validator` | plugin-dev | Validate plugin structure |
| `skill-reviewer` | plugin-dev | Review skill quality |
| `systems-architect` | built-in | System design decisions |
| `performance-tuner` | built-in | Performance optimization |
| `test-engineer` | built-in | Test creation |
| `refactor-expert` | built-in | Clean architecture |
| `root-cause-analyzer` | built-in | Deep debugging |
| `docs-writer` | built-in | Documentation |
| `security-auditor` | built-in | Security review |
| `config-safety-reviewer` | built-in | Config safety |
| `error-analyzer` | posthog | PostHog error patterns |

---

## Hooks (8)

Hooks run automatically before/after tool calls. Managed via `/hookify`. Current hooks come from:
- hookify (user-defined rules)
- code-review (auto-review triggers)
- Other plugins with PreToolUse/PostToolUse hooks

List active hooks: `/hookify:list`

---

## Hugging Face Skills (for ML work)

| Skill | What it does |
|---|---|
| `hugging-face-model-trainer` | Fine-tune LLMs (SFT, DPO, GRPO) |
| `hugging-face-vision-trainer` | Train object detection / image classification |
| `hugging-face-datasets` | Create and manage HF datasets |
| `hugging-face-jobs` | Run compute jobs on HF infrastructure |
| `hugging-face-evaluation` | Add eval results to model cards |
| `hugging-face-paper-publisher` | Publish research papers on HF |
| `hugging-face-trackio` | Track training experiments |
| `hugging-face-dataset-viewer` | Explore datasets via API |
| `huggingface-gradio` | Build Gradio web UIs |
| `transformers.js` | Run ML models in JavaScript |
| `hf-cli` | HF Hub CLI operations |

---

## PostHog Skills (for analytics)

| Command | What it does |
|---|---|
| `/posthog:query` | Run HogQL / natural language analytics |
| `/posthog:insights` | Query analytics and insights |
| `/posthog:flags` | Manage feature flags |
| `/posthog:experiments` | Manage A/B tests |
| `/posthog:errors` | View error tracking data |
| `/posthog:dashboards` | Manage dashboards |
| `/posthog:surveys` | Manage surveys |
| `/posthog:logs` | Query logs |
| `/posthog:search` | Search across all entities |
| `/posthog:workspace` | Manage orgs and projects |
| `/posthog:actions` | Manage reusable event definitions |
| `/posthog:llm-analytics` | Track LLM/AI costs |
| `/posthog:docs` | Search PostHog docs |
| `posthog-instrumentation` | Auto-add analytics to code |

---

## Workflow Combos (power moves)

**Ship a feature fast:**
```
/superpowers:brainstorming → /superpowers:writing-plans → /feature-dev → /review → /commit-push-pr
```

**Debug a production issue:**
```
/incident-response → /superpowers:systematic-debugging → /commit → /deploy-validate
```

**Clean up tech debt:**
```
/debt-analysis → /code-health → /simplify → /review → /commit
```

**Security review before deploy:**
```
/audit → /vulnerability-scan → /compliance-check → /deploy-validate
```

**Iterative refinement:**
```
/ralph-loop "improve test coverage for auth module" --max-iterations 5
```

**Create a new tool:**
```
/create-plugin → /skill-creator → /hookify (add guardrails)
```
