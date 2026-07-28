---
id: slash-commands
title: Slash Commands
sidebar_position: 7
---

# Slash Commands

Eleven prompt commands are configured (verified 2026-06-05 via the prompts API). Type `/` in the chat box to invoke one. Commands marked with a variable expect an argument.

## DHG operations (5)

| Command | Argument | Purpose |
|---------|----------|---------|
| `/health` | — | Run a comprehensive health check of the DHG AI Factory platform (uses System Health tool). |
| `/search` | `{{query}}` | Search the DHG knowledge base for the given query (uses Knowledge Search tool). |
| `/logs` | `{{container}}` | Query logs for the named container (uses Log Query tool). |
| `/backlog` | — | Review the current backlog of deferred work items (uses System Health tool). |
| `/debug` | `{{issue}}` | Start a structured debug session for an issue, following the DHG Debug Protocol. |

## Debug Ops engineering (5)

| Command | Argument | Purpose |
|---------|----------|---------|
| `/rca` | `{{PROBLEM}}` | Senior debug engineer performs root-cause analysis. |
| `/hypothesis` | `{{BUG}}` | Form ranked hypotheses for a bug. |
| `/trace` | `{{TARGET}}` | Trace an execution path through the codebase. |
| `/postmortem` | `{{INCIDENT}}` | Write an incident postmortem. |
| `/explain` | code / selection | Explain code to a technical architect. |

## Security (1)

| Command | Argument | Purpose |
|---------|----------|---------|
| `/security-review` | — | Run a high-signal security review (skill-style prompt). |

## Notes

- The operations commands are thin wrappers that instruct the model to call the matching DHG tool, so they work best on the six text models that carry all three tools.
- The Debug Ops commands are pure prompt scaffolds (no tool dependency) and work on any model.
