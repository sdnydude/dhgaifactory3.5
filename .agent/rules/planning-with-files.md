# Planning with Files (MANDATORY)

> **RULE 0 (ABSOLUTE):** Never lie, sugarcoat, or hide the truth. See `honesty.md`

## When This Applies

For ANY task requiring 5+ tool calls or spanning multiple sessions, you MUST use file-based planning.

## Required Files

Create these in the **project directory** (not .agent):

| File | Purpose |
|------|---------|
| `task_plan.md` | Phases, goals, progress, decisions |
| `findings.md` | Research discoveries, technical notes |
| `progress.md` | Session logs, work done, blockers |

## Mandatory Behaviors

### 1. Plan Before Action
Never start complex work without creating `task_plan.md` first.

### 2. The 2-Action Rule
After every 2 view/browser/search operations, IMMEDIATELY save key findings to files.

### 3. Read Before Decide
Before any major decision, read the plan file to refresh goals in context.

### 4. Update After Act
After completing any phase:
- Mark tasks complete: `[ ]` → `[x]`
- Update phase status
- Log errors encountered
- Note files created/modified

### 5. Log ALL Errors
Every error goes in task_plan.md:
```markdown
## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
```

### 6. Never Repeat Failures
If an action failed, the next action MUST be different. Track attempts, mutate approach.

## The 3-Strike Protocol

```
ATTEMPT 1: Diagnose & Fix
  → Read error carefully
  → Identify root cause
  → Apply targeted fix

ATTEMPT 2: Alternative Approach
  → Same error? Try different method
  → NEVER repeat exact same failing action

ATTEMPT 3: Broader Rethink
  → Question assumptions
  → Search for solutions
  → Update the plan

AFTER 3 FAILURES: Escalate to User
  → Explain what you tried
  → Share the specific error
  → Ask for guidance
```

## Session Start

1. Check for existing planning files
2. If found: Read all three files to recover context
3. If not found AND task is complex: Create them

## Session End

1. Update all planning files with current state
2. Sync to database (see `/planning-sync` workflow)
3. Never leave in-progress items unmarked

## The 5-Question Test

Before ending ANY session, verify you can answer:

| Question | Answer Source |
|----------|---------------|
| Where am I? | Current phase in task_plan.md |
| Where am I going? | Remaining phases |
| What's the goal? | Goal statement in plan |
| What have I learned? | findings.md |
| What have I done? | progress.md |

## Database Sync

Planning files are synced to the CR database for:
- Knowledge search across projects
- Reporting and analytics
- Research and pattern detection
- Session recovery

Invoke `/planning-sync` at end of significant work sessions.

## Violations

The following are violations of this rule:
- Starting complex work without task_plan.md
- Making major decisions without re-reading the plan
- Ending a session without updating progress.md
- Repeating a failed approach without trying alternatives
- Not logging errors encountered

## No Shortcuts

This rule exists because shortcuts cost time and money. The 3 minutes spent maintaining planning files saves hours of lost context and repeated mistakes.
