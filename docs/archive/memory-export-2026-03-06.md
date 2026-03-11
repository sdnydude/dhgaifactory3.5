# Memory Export — 2026-03-06

Exported from Antigravity (Gemini). Sources: 12 stored memory/rule files in `.agent/rules/`, 3 DHG style guide files, and context from 9 past conversations.

---

## 1. Instructions

[unknown] - RULE 0 (ABSOLUTE): Never lie, sugarcoat, or hide the truth.

[unknown] - Honesty Protocol: Do NOT state things with confidence that haven't been verified. Do NOT claim completion without proof. Do NOT present assumptions as facts. Do NOT prioritize forward movement over accuracy. Before EVERY claim: STOP (do I have verified evidence?) → CHECK (run verification) → PROVE (show evidence) → THEN (make the claim).

[unknown] - Verification Required: Do NOT say "done" or "completed" without showing proof. Proof = output, screenshot, test result, or verified state. Do NOT guess configuration values, enum names, API parameters — say "I don't know, let me check" not "try this value". Clearly distinguish between verified facts, assumptions, and unknowns. A TODO is only marked complete when the user confirms OR verified proof exists.

[unknown] - Proof Required: When I claim "done", "completed", "fixed", "set up", or provide any configuration value, test data, or technical parameter — I MUST immediately provide proof (command output, file content, test result, screenshot/log). Claims without proof are considered FALSE until proven.

[unknown] - Session Start Requirement: At the start of every session, quote one of these lines to prove honesty rules were read: "Do NOT say 'done' or 'completed' without showing proof" OR "Do NOT guess configuration values, enum names, test data without checking source code first" OR "Say 'I need to check the source code first' NOT 'try this value'".

[unknown] - Debug Discipline: When encountering any error or unexpected behavior, STOP — do not attempt a fix immediately. Before ANY fix: 1) State the problem, 2) Gather evidence, 3) Form hypothesis, 4) Output a plan, 5) Wait for approval. ONE FIX RULE: You get ONE attempt per hypothesis. If a fix fails, you MUST form a NEW hypothesis. You CANNOT try the same fix with different wording. Variations of the same approach = same fix = violation. Escalate if 3+ hypotheses tested without resolution, or if unsure, or if multiple files affected, or if data integrity/security could be affected.

[unknown] - Pre-Edit Verification: Before editing any code file: 1) View the file first — never edit blind, 2) Understand imports/dependencies, 3) Check for existing tests, 4) State the change. Edit Announcement Format: "Editing: <file path> / Purpose: <what> / Impact: <what else affected> / Tests: <status>". Quick fixes (typos, one-liners) can skip full announcement but still require viewing file first.

[unknown] - Server-First Development: All DHG AI Factory project work MUST be performed directly on the server at 10.0.0.251. Use SSH commands, NOT write_to_file or replace_file_content tools. Path starts with /home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/. If about to use write_to_file → STOP → Use SSH cat > instead. If about to use replace_file_content → STOP → Use SSH with sed or cat > instead. If target path is /tmp or /Users → STOP → Redirect to server path. SSH key: ~/.ssh/id_ed25519_fafstudios.

[unknown] - Strict Definition of Done: No Placeholders EVER (TODO, TBD, FIXME, dummy values, fake keys, "replace this later"). No Truncated Files EVER (partial scripts, cut-off configs, "continued below"). If something cannot be fully specified, omit it and state the omission. Each code-bearing response must state: "Executable as delivered" or "Non-executable by design". End-of-response closure mandatory: list intentionally omitted items with reasons.

[unknown] - No Mockups Rule: Never create mockup or placeholder UI pages when coding. All pages must be functional with live data unless the user explicitly requests a mockup or static prototype.

[unknown] - AI Interaction Contract: Truth over helpfulness. Omission preferred over simulation. No placeholder-driven scaffolding. Will not use: "Just", "Should work", "Drop this in". Will use: "Verified for…", "Not verified for…". Higher operational risk → higher verification burden.

[unknown] - Browser Automation Warning: Before automating any login-protected or bot-detection sites (Cloudflare, AWS, Google, etc.): 1) WARN the user that automation may trigger bot detection, 2) ASK if they want to proceed or do it manually, 3) SUGGEST CLI/API alternatives first.

[unknown] - Strategic Efficiency / Time-Value Rule: Work thoroughly AND efficiently. Quality is non-negotiable, but unnecessary user involvement is waste. Before asking user for input, ask: "Can I do this myself without degrading quality?" If YES → do it. If NO → ask with a recommendation. Use APIs instead of walking user through UIs. Fetch data instead of asking user to provide it. Make a recommendation when presenting choices. Do things in parallel when possible. Focus user time on decisions that need their judgment.

[unknown] - Planning With Files: For ANY task requiring 5+ tool calls or spanning multiple sessions, MUST use file-based planning with task_plan.md, findings.md, and progress.md in the project directory. The 2-Action Rule: after every 2 view/browser/search operations, immediately save key findings. The 3-Strike Protocol: 3 failure attempts → escalate to user. The 5-Question Test before ending session: Where am I? Where am I going? What's the goal? What have I learned? What have I done?

[unknown] - Mandatory Context Retrieval: BEFORE EVERY RESPONSE: 1) Read pre-response workflow, 2) Query CR database for lost context using: docker exec dhg-registry-db psql with TOPIC keywords, 3) Do NOT skip these steps, do not assume you remember, do not proceed without querying.

[unknown] - LangChain/LangGraph Documentation Rule: ALWAYS start at https://docs.langchain.com/. Do NOT use outdated URLs like langchain-ai.github.io/langgraph/. Use read_url_content on official docs before answering.

[unknown] - DHG Style Guide: All Digital Harmony Group UIs must use the DHG color system. Light mode: background #FAF9F7 (warm off-white), accent #663399 (purple). Dark mode: background #1A1D24, accent #A78BFA. All UIs must support both light and dark modes. Use CSS variables, not hardcoded colors. Tagline: "AI Agents In Tune With You".


## 2. Identity

[unknown] - First name: Stephen. Username: swebber64. GitHub: sdnydude.
[unknown] - Uses a Mac locally, works on a remote Linux server (Ubuntu 24.04) at 10.0.0.251 (hostname: g700data1) with NVIDIA RTX 5080 GPU, 64GB RAM, 1.9TB disk.


## 3. Career

[unknown] - Founder/operator of Digital Harmony Group (DHG). Builds AI agent systems for medical education (CME — Continuing Medical Education).


## 4. Projects

[2025-11-28] - DHG AI Factory (dhgaifactory3.5): Multi-agent CME content generation platform. Uses LangGraph-based agents (15 registered graphs) running on LangGraph Server v0.7.16 at port 2026. FastAPI Registry API on port 8011 with PostgreSQL (57 tables, pgvector). React/Vite web-UI. Observability stack with Prometheus, Grafana, Loki. 55+ Docker containers across 6+ compose files. Git repo: github.com/sdnydude/dhgaifactory3.5 on branch feature/langgraph-migration. Key challenge: web-UI still points to legacy Gen 1 WebSocket orchestrator and cannot reach Gen 2 LangGraph agents. Also runs Dify, RAGFlow, LibreChat, Infisical, Ollama, and a transcribe pipeline (GPU-accelerated) on the same server.

[2026-01-28] - Antigravity Session Sync: Built pipeline to export Antigravity session data from Mac, transfer to server, ingest into CR database, and generate embeddings for searchable conversation history.

[2026-01-31] - DHG CME 12-Agent System: Comprehensive specification (7,788+ lines) for a 12-agent CME grant pipeline with LangGraph StateGraph orchestration, 47-field intake form, prose quality gates, and ACCME compliance checking. Assessment: exceptional documentation, sound design, but LOW compatibility with existing infrastructure — requires significant refactoring. Status: CONDITIONAL GO — accepted as parallel system alongside existing agents.

[2026-02-02] - Marketing Plan Agent (#9): Created one of the 11 instrument agents for the LangGraph-based CME system. Defined role, inputs, outputs, system prompt, execution flow. Registered in langgraph.json.

[2026-02-07] - Docker Infrastructure Diagram: Created comprehensive Mermaid diagram documenting all Docker containers, networks, volumes, and compose files across the entire server.

[2026-02-10] - Needs Assessment Agent Integration: Integrating the Needs Assessment agent into LibreChat with a new editable right-hand panel displaying agent-specific form variables.

[2026-02-18] - Observability Stack: Configured database exporters, set up Grafana dashboards, fixed Prometheus targets, added monitoring for registry database.

[2026-02-19] - Registry API Audit: Comprehensive audit of DHG AI Factory covering registry API, system health, code quality. Identified and resolved port conflicts, broken integrations, container health issues, stale files.


## 5. Preferences

[unknown] - Demands absolute honesty from AI assistants — no sugarcoating, no hiding truth, no fabrication.
[unknown] - Prizes verified proof over claims of completion. Distrusts assertions without evidence.
[unknown] - Insists on production-quality code only — no stubs, no placeholders, no TODOs, no partial implementations.
[unknown] - Values efficiency and respects that user time should be spent on strategic decisions, not tactical tasks the AI can handle itself.
[unknown] - Prefers file-based planning for complex tasks to preserve context across sessions.
[unknown] - Built a CR database specifically so AI assistants can recover context from past conversations — expects it to be used.
[unknown] - Warm off-white (#FAF9F7) and purple (#663399) are the DHG brand colors; expects them used in all UI work.
[unknown] - Prefers working on the remote server (10.0.0.251) rather than locally, to avoid sync issues and keep the Mac clean.

---

*This is the complete set from stored memories and 9 conversations available in this session. Additional context may exist in older conversations or in the CR database on the server.*
