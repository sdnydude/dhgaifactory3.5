# Plugins & Skills for Dummies

> A complete reference for every plugin, skill, and command available in the DHG AI Factory Claude Code environment.

---

## Enabled Plugins (18)

These are official Claude plugins configured in `.claude/settings.json`:

| Plugin | What It Does | How It Works |
|--------|-------------|--------------|
| **context7** | Fetches up-to-date docs & code examples for any library | Auto-activates when you ask about a library |
| **playwright** | Browser automation — click, type, screenshot, test | Use Playwright MCP tools or `/project:playwright` |
| **superpowers** | Enhanced workflows — planning, TDD, debugging, code review, parallel agents | Auto-activates based on task type |
| **frontend-design** | Generates production-grade UI components with high design quality | Triggers when building web components/pages |
| **code-review** | Code quality, best practices, bug detection | `/code-review` or auto on file changes |
| **feature-dev** | Guided feature development with architecture focus | `/feature-dev` to start guided workflow |
| **github** | GitHub integration — PRs, issues, repo management | Uses `gh` CLI under the hood |
| **commit-commands** | Git commit, push, PR creation helpers | `/commit`, `/commit-push-pr`, `/clean_gone` |
| **claude-md-management** | Manage and improve CLAUDE.md files | `/revise-claude-md`, `/claude-md-improver` |
| **code-simplifier** | Simplifies and refines code for clarity | `/simplify` after making changes |
| **ralph-loop** | Iterative execution loop with feedback | `/ralph-loop` to start, `/cancel-ralph` to stop |
| **hookify** | Create hooks to prevent unwanted Claude behaviors | `/hookify` to analyze and create hooks |
| **agent-sdk-dev** | Build Claude Agent SDK apps | `/new-sdk-app` to scaffold a new app |
| **skill-creator** | Create, modify, and benchmark custom skills | Use when building new skills |
| **claude-code-setup** | Analyze codebase and recommend Claude Code automations | Suggests hooks, skills, MCP servers |
| **typescript-lsp** | TypeScript language intelligence | Auto-activates on .ts/.tsx files |
| **pyright-lsp** | Python language intelligence | Auto-activates on .py files |
| **playground** | Creates interactive HTML playgrounds | `/playground` to build visual explorers |

---

## Slash Commands — Quick Reference

Type these directly in the Claude Code prompt:

### Git & Workflow

| Command | What It Does |
|---------|-------------|
| `/commit` | Stage changes and create a conventional commit |
| `/commit-push-pr` | Commit, push, and open a GitHub PR in one step |
| `/clean_gone` | Delete local branches whose remotes are gone |

### Code Quality

| Command | What It Does |
|---------|-------------|
| `/simplify` | Review recently changed code for reuse and quality |
| `/code-review` | Full code review with security and performance analysis |
| `/review` | Comprehensive review using specialized agents |

### Planning & Development

| Command | What It Does |
|---------|-------------|
| `/feature-dev` | Guided feature development with codebase analysis |
| `/frontend-design` | Build distinctive, production-grade UI components |
| `/playground` | Create an interactive HTML playground/explorer |

### Documentation

| Command | What It Does |
|---------|-------------|
| `/revise-claude-md` | Update CLAUDE.md with learnings from this session |
| `/claude-md-improver` | Audit and improve all CLAUDE.md files in the repo |
| `/docs-gen` | Auto-generate documentation from code |
| `/api-documenter` | Generate OpenAPI/Swagger specs from code |

### Security & Quality

| Command | What It Does |
|---------|-------------|
| `/audit` | Comprehensive multi-phase security audit |
| `/vulnerability-scan` | Deep vulnerability analysis with CVE scanning |
| `/compliance-check` | Regulatory compliance validation (GDPR, SOC2, HIPAA, etc.) |
| `/secret-scanner` | Detect exposed secrets, API keys, and credentials |
| `/dependency-auditor` | Check dependencies for known vulnerabilities |

### Testing & Performance

| Command | What It Does |
|---------|-------------|
| `/test-gen` | Generate comprehensive test suites automatically |
| `/profile` | Performance profiling with bottleneck identification |
| `/benchmark` | Load testing and performance benchmarking |

### Operations

| Command | What It Does |
|---------|-------------|
| `/health-check` | System health verification for production monitoring |
| `/deploy-validate` | Pre-deployment validation (tests, security, config) |
| `/incident-response` | Production incident coordination and RCA |
| `/code-health` | Codebase health assessment with quality metrics |
| `/debt-analysis` | Technical debt identification with refactoring roadmap |

### Task Management

| Command | What It Does |
|---------|-------------|
| `/todo-add` | Add a todo item to TO-DOS.md |
| `/todo-check` | List outstanding todos and pick one to work on |
| `/whats-next` | Create a handoff document for continuing work later |
| `/handoff-create` | Same as whats-next — session handoff document |

### Automation

| Command | What It Does |
|---------|-------------|
| `/hookify` | Analyze conversation and create behavioral hooks |
| `/ralph-loop` | Start an iterative execution loop |
| `/cancel-ralph` | Stop an active Ralph Loop |
| `/prompt-run` | Delegate prompts to fresh sub-task contexts |
| `/scaffold` | Generate production-ready project structures |

---

## DHG Project Commands (8)

Custom commands specific to the DHG AI Factory. Invoke with `/project:name`:

| Command | Invocation | What It Does |
|---------|-----------|--------------|
| **Docker Expert** | `/project:docker-expert` | Container orchestration, networking, health checks, security hardening |
| **FastAPI Pro** | `/project:fastapi-pro` | REST endpoints, Pydantic schemas, SQLAlchemy models, Prometheus metrics |
| **LangGraph Architect** | `/project:langgraph` | Agent design, state management, async nodes, orchestrators, quality gates |
| **Observability Engineer** | `/project:observability-engineer` | Prometheus scrape jobs, alert rules, Grafana dashboards, Loki ingestion |
| **Grafana Dashboards** | `/project:grafana-dashboards` | Dashboard JSON, Prometheus panels, RED/USE methodology |
| **Postgres Best Practices** | `/project:postgres-best-practices` | Query optimization, indexing, connection management, RLS policies |
| **Playwright Automation** | `/project:playwright` | Browser testing, form validation, responsive design, accessibility |
| **Prometheus Config** | `/project:prometheus-configuration` | Prometheus scrape targets and configuration |

### Example Usage

```
/project:docker-expert add a healthcheck to the dhg-langgraph-api service
/project:langgraph create a new fact-checking agent
/project:fastapi-pro add a CRUD endpoint for agent run history
/project:observability-engineer add a scrape job for dhg-langgraph-api
```

---

## Superpowers Skills (Auto-Triggered)

These activate automatically based on what you're doing. No slash command needed:

| Skill | When It Activates |
|-------|------------------|
| **Brainstorming** | Before any creative work — features, components, modifications |
| **Writing Plans** | When you have a spec or requirements for a multi-step task |
| **Executing Plans** | When implementing a written plan in a separate session |
| **Test-Driven Development** | Before writing implementation code for features or bugfixes |
| **Systematic Debugging** | When encountering any bug, test failure, or unexpected behavior |
| **Subagent-Driven Development** | When executing plans with independent tasks |
| **Dispatching Parallel Agents** | When facing 2+ independent tasks without shared state |
| **Verification Before Completion** | Before claiming work is complete or creating PRs |
| **Requesting Code Review** | When completing tasks or implementing major features |
| **Receiving Code Review** | When processing code review feedback |
| **Using Git Worktrees** | When feature work needs isolation from current workspace |
| **Finishing a Dev Branch** | When implementation is complete and ready to integrate |
| **Writing Skills** | When creating or editing custom skills |

---

## Specialized Agents (via Agent Tool)

These run as sub-processes for complex tasks:

| Agent | Purpose |
|-------|---------|
| **Explore** | Fast codebase exploration — find files, search code, answer architecture questions |
| **Plan** | Software architect — design implementation plans, identify critical files |
| **code-reviewer** | Review code against plan and coding standards |
| **code-explorer** | Trace execution paths, map architecture layers |
| **code-architect** | Design feature architectures from existing patterns |
| **code-simplifier** | Simplify code for clarity and maintainability |
| **test-engineer** | Comprehensive test creation and quality assurance |
| **refactor-expert** | Clean architecture, SOLID principles, tech debt reduction |
| **root-cause-analyzer** | Deep debugging and root cause analysis |
| **docs-writer** | Technical documentation — API docs, user guides |
| **security-auditor** | Vulnerability assessment, OWASP compliance |
| **performance-tuner** | Profiling, optimization, scalability |
| **systems-architect** | Evidence-based design decisions, scalable patterns |
| **config-safety-reviewer** | Production reliability — pool sizes, timeouts, limits |

---

## External Skills Library (552+)

Located in `.agent/skills/`, organized by category:

| Category | Count | Key Skills |
|----------|-------|-----------|
| **Architecture** | 52 | architect-review, c4-context, monorepo-architect, parallel-agents |
| **Business** | 35 | copywriting, seo-fundamentals, pricing-strategy, marketing-ideas |
| **Data & AI** | 81 | rag-engineer, prompt-engineer, langgraph, agent-evaluation |
| **Development** | 72 | typescript-expert, python-patterns, react-patterns, error-handling |
| **General** | 95 | brainstorming, doc-coauthoring, writing-plans |
| **Infrastructure** | 72 | docker-expert, aws-serverless, kubernetes, terraform, ci-cd |
| **Security** | 107 | api-security, vulnerability-scanner, sql-injection-testing |
| **Testing** | 21 | test-driven-development, testing-patterns, test-fixing |
| **Workflow** | 17 | workflow-automation, inngest, trigger-dev |

---

## MCP Servers (2)

Model Context Protocol servers providing external tool access:

| Server | Tools Provided | Status |
|--------|---------------|--------|
| **Context7** | `resolve-library-id`, `query-docs` — fetch live documentation for any library | Active |
| **Playwright** | 20+ browser tools — navigate, click, type, screenshot, evaluate JS, manage tabs | Active |

---

## Cheat Sheet

```
# Most useful day-to-day commands:
/commit                              # Quick commit
/commit-push-pr                      # Ship it
/review                              # Full code review
/simplify                            # Clean up what you just wrote
/test-gen                            # Generate tests
/project:langgraph [task]            # LangGraph agent work
/project:docker-expert [task]        # Docker/compose help
/project:fastapi-pro [task]          # API endpoint work
/todo-check                          # What should I work on next?
/whats-next                          # Create handoff for next session
```
