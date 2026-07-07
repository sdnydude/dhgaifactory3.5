# Capture Common — shared mechanics for every auto-*-capture rule

Each `auto-*-capture.md` rule references this file for the mechanics they all share. Rule-specific triggers, fields, and category tables stay in their own rule.

## Firing
- **Automated — don't ask permission.** Fire whenever the rule's trigger condition is met; never ask "should I capture this?"
- **Fire-and-forget.** The script exits 0 on failure, so a down registry never blocks the session.
- **Exempt from the planning-phase command gate.** A capture POST is a metadata write, not a project/production change (see quality-first.md), so fire it even mid-planning.

## Honesty on failure
- **Announce only on failure.** On success, stay silent. When the registry is unreachable the script prints a "...dead-lettered..." line — repeat that one line to Stephen so he knows the capture is queued, not landed. Say "capture queued," never "captured" (see honesty-protocol.md).

## Payload
- **No shell-escaping needed.** The payload travels via a `--stdin` quoted heredoc, so apostrophes and shell metacharacters are inert. (This is shell escaping only — an embedded double-quote inside a JSON string value still needs `\"`, since the registry parses the payload as JSON server-side.)
- **`model_name`** is the current session's model ID — never hardcode it.
- **`session_id`**: the conversation/session ID if available, else `null`.
- **Endpoint:** always the LAN IP `10.0.0.251:8011` — never `localhost`.
- Include `tags` that aid future semantic search.
