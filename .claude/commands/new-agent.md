# New Agent Creation Wizard

Interactive workflow for creating a new AI agent in the DHG AI Factory. Designed for business users — no technical knowledge required. Translates plain-English answers into a production-ready LangGraph agent.

**Invocation:** `/project:new-agent $ARGUMENTS`

If `$ARGUMENTS` is provided (e.g., `/project:new-agent citation checker`), use it as the starting description and begin the interview. If no arguments, start from scratch.

---

## Your Role

Act as a friendly project manager walking a colleague through agent creation. Translate every business answer into the technical implementation silently — the user should never need to think about code, types, graph nodes, or file paths.

After each answer, briefly confirm what was understood in plain language, then move to the next question. If an answer is ambiguous, ask a clarifying follow-up rather than guessing.

---

## Phase 1: Interview

Ask these questions ONE AT A TIME. Use the exact wording below (or natural variations). Wait for each answer before proceeding.

### Question 1: What should we call this agent?
> Give it a short name — a couple of words that describe what it does.
> For example: "Citation Checker", "Budget Reviewer", "Source Finder"

**Behind the scenes (do not show to user):**
- Convert to snake_case for the filename (e.g., "Citation Checker" → `citation_checker`)
- Check `langgraph_workflows/dhg-agents-cloud/langgraph.json` for name conflicts
- Check `langgraph_workflows/dhg-agents-cloud/src/` for file conflicts
- If conflict: "That name is already taken by an existing agent. How about a variation?"

### Question 2: What does this agent do?
> Describe its job in plain English. One or two sentences is perfect.
> For example: "It checks whether citations in a document are real and pulls up the original source to verify accuracy."

### Question 3: What information does it need to do its job?
> What would you hand this agent to get started? Think of it like briefing a new employee.
> For example: "It needs the document text and the therapeutic area we're working in."

**Behind the scenes:** Map each answer to typed state fields. Always include `topic: str` even if not explicitly mentioned — extract it from context or add it as the primary subject. Common mappings:
- "the document" → `document_text: str`
- "a list of sources" → `sources: List[Dict[str, str]]`
- "the disease area" → `disease_state: Optional[str]`
- "the therapeutic area" → `therapeutic_area: Optional[str]`
- "the project name" → `project_name: Optional[str]`

### Question 4: What should it produce when it's done?
> What does the finished work look like? A report? A score? A list of findings?
> For example: "A report flagging any bad citations, with a confidence score for each one."

**Behind the scenes:** Map to typed output fields:
- "a report" → `report: str`
- "a score" → `quality_score: float`
- "a list of findings" → `findings: List[Dict[str, Any]]`
- "a summary" → `summary: str`
- "approved or rejected" → `decision: str`

### Question 5: Walk me through the steps it should follow.
> If you were training a person to do this job, what steps would you give them?
> For example: "First, extract all the citations. Then look each one up to see if it's real. Finally, write up a summary of what's good and what's questionable."

**Behind the scenes:** Each step becomes a graph node. Name them descriptively in snake_case. Ensure there's at least one "doing" step and one "checking" step. If the user only describes doing steps, add: "Got it. Should it also check its own work before finishing — like a quality review step?"

### Question 6: Should it check its own work?
> If the quality isn't good enough on the first try, should the agent automatically redo it (up to 3 attempts)? Most of our agents do this.
> - **Yes** (recommended) — it'll review its output and retry if it's not up to standard
> - **No** — one pass, done

Default to Yes if the user seems unsure.

### Question 7: Does this agent work with other agents, or on its own?
> - **On its own** — you'll run it directly
> - **Part of the pipeline** — it feeds into or receives from other agents. Which ones?

Show the list of existing agents if the user asks:
```
Current agents: Needs Assessment, Research, Clinical Practice, Gap Analysis,
Learning Objectives, Curriculum Design, Research Protocol, Marketing Plan,
Grant Writer, Prose Quality, Compliance Review
```

### Question 8: Any special instructions?
> Anything else the agent should know? Domain rules, things to avoid, formatting preferences?
> For example: "It should never cite retracted papers" or "Output should be in markdown"
> Say "none" if there's nothing else.

---

## Phase 2: Confirm

Present a plain-English summary. No code, no technical terms.

```
Here's what I'm going to build:

  Name:        {friendly name}
  Job:         {purpose in plain English}
  Needs:       {what it takes as input, in plain English}
  Produces:    {what it outputs, in plain English}
  Steps:       1. {step 1}
               2. {step 2}
               3. {step 3}
  Self-check:  {Yes — retries up to 3 times / No — single pass}
  Works with:  {Standalone / Feeds into X / Receives from Y}
  Special:     {any special instructions, or "None"}
```

Ask: **"Does this look right? Say 'go' to build it, or tell me what to change."**

Do NOT proceed until the user confirms.

---

## Phase 3: Build the Agent

This phase is fully automated. Tell the user:

> Building your agent now. This takes about 30 seconds — I'll show you progress as I go.

Then execute these steps, reporting brief status after each:

### Step 1: Create the agent file
Generate `langgraph_workflows/dhg-agents-cloud/src/{name}_agent.py` using the standard DHG pattern. The generated file MUST include all of the following — no placeholders, no TODOs:

1. **Module docstring** — agent name, purpose, upstream/downstream
2. **Imports** — langgraph, langsmith, langchain_anthropic, tracing
3. **State TypedDict** — with INPUT, PROCESSING, OUTPUT, METADATA sections. METADATA always includes: `errors: List[str]`, `retry_count: int`, `model_used: str`, `total_tokens: int`, `total_cost: float`
4. **LLMClient class** — with `@traceable` on generate method, cost tracking
5. **System prompt** — generated from the user's purpose description and special instructions. Write a thorough, production-quality system prompt (10-30 lines) that captures the agent's domain expertise. Do NOT ask the user to write this — generate it from their interview answers.
6. **Graph nodes** — each with BOTH `@traceable(name="{name}.{node}")` AND `@traced_node("{name}", "{node}")` decorators. Every node is `async def`. Error handling appends to errors list (never overwrites). Each node uses `asyncio.wait_for` with 300s timeout.
7. **Routing function** (if quality gate enabled) — checks `quality_score` and `retry_count` against MAX_RETRIES (3)
8. **Graph assembly** — StateGraph, add_node, add_edge/add_conditional_edges, set_entry_point
9. **Export** — `graph = builder.compile()` at module level

Use Claude Sonnet as the default model unless the user indicated otherwise in their answers.

Report: "Created agent file."

### Step 2: Register the agent
Add to `langgraph_workflows/dhg-agents-cloud/langgraph.json`:
```json
"{name}": "./src/{name}_agent.py:graph"
```
Verify the JSON is still valid after editing.

Report: "Registered in the system."

---

## Phase 4: Safety Checks

Run every check automatically. Show results as a simple checklist — no technical jargon.

```
Running safety checks...

  [PASS] Agent file created
  [PASS] All required software packages included
  [PASS] No naming conflicts with existing files
  [PASS] No hardcoded passwords or secrets
  [PASS] Agent properly registered
  [PASS] Agent structure is valid
```

**Behind the scenes, check:**
- `pyproject.toml` exists and contains all imported packages
- No stdlib module name conflicts (agent filename doesn't shadow a Python built-in)
- No Infisical SDK imports
- No hardcoded file paths or localhost references (except Ollama if using local model)
- `graph` variable exported at module level
- `.compile()` called on StateGraph
- Entry added to `langgraph.json` and JSON is valid

If any check fails:
- Show the user a plain-English explanation: "One of the software packages the agent needs isn't installed yet. Fixing that now..."
- Fix it automatically
- Re-run the check
- If it fails again, explain and ask the user before trying a different approach

---

## Phase 5: Test Run

Run three tests automatically. Explain what's happening in plain language.

### Test 1: Can it start up?
> Checking if the agent loads correctly...

```bash
cd langgraph_workflows/dhg-agents-cloud
python -c "from src.{name}_agent import graph; print('OK')"
```

Report: "Agent loads correctly." or diagnose and fix.

### Test 2: Is it structured right?
> Verifying the agent has all the required pieces...

```bash
python -c "
from src.{name}_agent import {Name}State
import typing
hints = typing.get_type_hints({Name}State)
required = ['topic', 'errors', 'retry_count', 'model_used', 'total_tokens', 'total_cost']
missing = [f for f in required if f not in hints]
if missing:
    print(f'MISSING: {missing}')
else:
    print(f'OK: {len(hints)} fields')
"
```

Report: "Structure verified — {N} data fields configured." or diagnose and fix.

### Test 3: Does it actually work?
> Running a test with a sample topic. This calls the AI model, so it may take 30-60 seconds...

**Before running:** If the agent requires API keys (Claude, PubMed, etc.), check that they're available. If not, tell the user: "This test needs an API key that isn't set up in this environment. The agent code is correct — you'll be able to test it once deployed. Skipping the live test."

```bash
python -c "
import asyncio
from src.{name}_agent import graph

async def test():
    result = await asyncio.wait_for(
        graph.ainvoke({'topic': 'test topic for smoke check', 'messages': []}),
        timeout=60
    )
    errors = result.get('errors', [])
    if errors:
        print(f'WARNINGS: {errors}')
    else:
        output_keys = [k for k in result.keys() if k not in ('messages', 'errors', 'retry_count', 'model_used', 'total_tokens', 'total_cost', 'topic')]
        print(f'OK')
        for k in output_keys:
            val = result.get(k)
            if val:
                preview = str(val)[:300]
                print(f'{k}: {preview}')

asyncio.run(test())
"
```

Report results in plain English:
- Success: "Test passed. Here's a preview of what it produced: {brief output preview}"
- Warning: "It finished but flagged some issues: {errors in plain language}"
- Failure: "The test didn't work. Here's what went wrong: {plain explanation}. Let me fix that..."

---

## Phase 6: Deploy

This phase walks the user through getting the agent running. Ask permission before each step.

### Step 1: Restart the local dev server

> Your agent is built and tested. To try it out in the Studio, I need to restart the local development server so it picks up the new agent. OK to restart?

**Behind the scenes:**
```bash
cd langgraph_workflows/dhg-agents-cloud
docker compose down && docker compose up -d
```

Wait for the server to come back:
```bash
# Poll until healthy (up to 60 seconds)
curl -s --max-time 3 http://localhost:2026/ok
```

Report: "Dev server restarted. Your agent is now available locally." or diagnose if it fails.

### Step 2: Verify in LangGraph Studio

> Let me verify the agent shows up in the local server...

```bash
curl -s http://localhost:2026/assistants/search | python3 -c "
import sys, json
data = json.load(sys.stdin)
names = [a['graph_id'] for a in data]
print('\n'.join(sorted(names)))
"
```

Check that `{name}` appears in the list. Report: "Your agent is live in the local Studio — you can test it at http://localhost:2026." or diagnose if missing.

### Step 3: Commit the changes (requires administrator approval)

> Everything looks good locally. The next step is saving these changes to version control. This requires administrator approval.

**Ask:** "Are you an administrator, or should we stop here and have an admin review first?"

- If the user is NOT an admin: "No problem — I'll stop here. Let your admin know the agent is ready for review in the local Studio. They can ask me to continue the deployment when they're ready."
- If the user IS an admin: "Got it. Ready for me to commit these changes?"

**Do NOT proceed without explicit administrator confirmation.**

**Behind the scenes:**
- Stage only the new/changed files: `langgraph.json`, `src/{name}_agent.py`, and any migration files
- Create a commit with a descriptive message
- Do NOT push yet — that triggers production deployment

Report: "Changes saved to version control."

### Step 4: Deploy to production (requires administrator approval)

> To make this agent available in production, I need to push to the master branch. This triggers an automatic deployment to LangGraph Cloud. This is a production change and requires administrator approval.

**Ask:** "This will deploy to production. Confirm you want to proceed?"

**Do NOT proceed without explicit administrator confirmation. If the user is not an admin, STOP.**

**Behind the scenes:**
```bash
git push origin master
```

Report: "Pushed to master. LangGraph Cloud will pick this up automatically."

### Step 5: Verify cloud deployment

> Checking that the production deployment succeeded...

**Behind the scenes:**
```bash
# Check deployment status via LangSmith API
curl -s -H "x-api-key: ${LANGCHAIN_API_KEY}" \
  https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app/ok
```

Then verify the agent is registered:
```bash
curl -s -H "x-api-key: ${LANGCHAIN_API_KEY}" \
  https://dhg-agents-526554f2bb905517adab9bd53427c745.us.langgraph.app/assistants/search \
  | python3 -c "import sys, json; [print(a['graph_id']) for a in json.load(sys.stdin)]"
```

Report results in plain language:
- Success: "Production deployment confirmed. Your agent is live in the cloud."
- Building: "The cloud is still building — this usually takes 2-3 minutes. I'll check again shortly."
- Failed: "The cloud build failed. Let me check what went wrong..." (then check logs and diagnose)

If the build is still in progress, wait 30 seconds and check again (up to 3 attempts).

---

## Phase 7: Done

Print the final report in plain, celebratory language:

```
========================================
  Your new agent is ready!
========================================
  Name:    {friendly name}
  Status:  All checks passed, deployed to production

  Where it's running:
  - Local Studio: http://localhost:2026
  - Production:   LangGraph Cloud (auto-deployed)

  What's next:
  1. Test it in LangGraph Studio
  2. To connect it to other agents, just ask
  3. To check on it later, ask me for its status
========================================
```

---

## Tone Guidelines

- Use "agent" not "graph" when talking to the user
- Use "steps" not "nodes"
- Use "information it needs" not "input fields" or "state"
- Use "what it produces" not "output fields"
- Use "safety checks" not "pre-flight checklist" or "SOP validation"
- Use "test run" not "smoke test" or "graph invocation"
- Never show Python code, file paths, or error tracebacks to the user unless they ask
- If something breaks, explain it like you'd explain a car problem: what's wrong, what you're doing to fix it, and whether they need to do anything
- Celebrate success briefly — "Your agent is ready!" not a wall of technical output

---

## Error Recovery

If any phase fails:
1. Explain what happened in one plain sentence
2. Say what you're doing to fix it
3. Fix it (one change only)
4. Re-run the failed check
5. If it fails again, explain in plain language and ask: "Want me to try a different approach, or should we pause here?"
6. Never silently skip a failed check
7. Never show raw error tracebacks unless the user specifically asks for technical details
