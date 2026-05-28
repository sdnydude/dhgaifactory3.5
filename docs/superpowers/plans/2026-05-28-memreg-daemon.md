# dhg-memreg-agent Daemon — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python polling daemon that runs all memreg pipeline operations (captures, DLQ retry, ingestion, materialization, metrics) as the main process of the dhg-memreg Docker container.

**Architecture:** Single Python process polls `~/.claude/projects/*/*.jsonl` every 30s. When per-session token growth ≥ 100K (tiktoken cl100k_base), runs a 9-step sweep with per-step threading timeouts. Steps reuse existing capture/ingestion logic via Python imports (no subprocess). Failed POSTs go to a dead-letter queue, retried each sweep.

**Tech Stack:** Python 3.12, tiktoken 0.7.0 (tokenizer), httpx (HTTP), prometheus_client (metrics), stdlib `http.server` (health endpoint), `concurrent.futures.ThreadPoolExecutor` (step timeouts), `fcntl.flock` (file locking). Docker base: `python:3.12-slim`. Runs as UID 1000 (matches host `swebber64`).

**Spec:** `docs/superpowers/specs/2026-05-28-memreg-daemon-design.md`

**Repo:** `~/DHG/dhg-memreg` (github.com/sdnydude/dhg-memreg) — daemon code lives here. Container runs in the aifactory3.5 docker-compose.

**Advisor findings incorporated:** C1 (sys.path mount path), C2 (pinned tiktoken + smoke test), C3 (safe newline-boundary offsets), I1 (threading not asyncio), I2 (fcntl.flock on DLQ), I3 (two-tier SweepContext), I4 (restart honors offsets), I5 (atomic state writes), G2 (cl100k_base documented), G3 (USER directive UID 1000).

---

## Revisions (post advisor review 2)

This plan was revised after a second advisor review found:

1. **Registry sort-order bug (CRITICAL):** `deferred_items_service.py:81` orders by `created_at DESC` with `limit=5`. Items older than the 5 newest never resurface, causing the user's reported "lost deferred items" problem. The daemon cannot fix this without a registry-side fix first. **Added as Task 0 (prerequisite).**
2. **No `last_surfaced_at` field** in the deferred_items schema. Required to track which items were already surfaced this cycle. Added to Task 0.
3. **Task 6 was not a real task** — merged into Task 5.
4. **Step 9 metrics injection was hack-on-hack.** Replaced with direct `metrics.record_*()` calls in `main()` after `runner.run()` returns. Step 9 removed from sweep.
5. **ENDPOINTS dict duplicated** between `memreg_capture.py` and `daemon/dlq.py`. DLQ now imports from memreg_capture.
6. **`BATCH_DATE` set at module import time** — daemon would tag documents with the wrong date after midnight. Set per-call now.
7. **80-line custom HTTP server** replaced with `prometheus_client.start_http_server()` + minimal /health handler.
8. **`globals()` monkey-patch in `extract_capture_payloads`** replaced with explicit `project_name` parameter through `build_*_payload` functions.
9. **`sys.argv` mutation in ingest steps** replaced with `argv=None` parameter on each script's `main()` function.
10. **tiktoken `cl100k_base` "closest to Claude's tokenizer" claim** reframed as an approximation (no citation exists; threshold is configurable; precision not critical).
11. **Task 13 (rules-tier briefing) hardened** with kill switch, quality gate (count_7d ≥ 2), TTL (stale-delete if registry unreachable), observability endpoint, `00-` filename prefix (load-first), and oldest-first deferred items section.

Net: **23 tasks** (was 22; merged 5/6 and added Task 0).

---

## Task Map

| # | Task | Files | Risk |
|---|------|-------|------|
| 0 | **Registry fix: deferred-items sort + `last_surfaced_at`** (prerequisite) | registry/deferred_items_service.py, registry/deferred_items_endpoints.py, registry/models.py, migration | medium |
| 1 | Daemon package + poller (tiktoken) | daemon/__init__.py, daemon/poller.py | low |
| 2 | Dead-letter queue (imports ENDPOINTS from memreg_capture) | daemon/dlq.py | low |
| 3 | Sweep runner (threading timeouts) | daemon/sweep.py | low |
| 4 | Refactor capture-guarantee — add `project_name` param (no globals()) | hooks/capture-guarantee.py | medium |
| 5 | Step 1 (capture-guarantee) + Step 2 (DLQ retry) | daemon/steps.py | medium |
| 6 | Mtime tracker for ingestion | daemon/mtime_tracker.py | low |
| 7 | Add `argv=None` to ingest `main()` functions | scripts/ingest-memory-files.py, scripts/ingest-claude-md.py | low |
| 8 | Step 3 (ingest memory files) — uses `main(argv=[...])` | daemon/steps.py | medium |
| 9 | Step 4 (ingest CLAUDE.md) — uses `main(argv=[...])` + sys.path fix | daemon/steps.py, scripts/ingest-claude-md.py | medium |
| 10 | Step 5 (CodeGraph batch sync) | daemon/steps.py | low |
| 11 | Step 6 (materialize KB briefing) — uses oldest-first deferred sort | daemon/steps.py | low |
| 12 | Step 7 (Serena digests) | daemon/steps.py | low |
| 13 | Step 8 (rules-tier briefing) — hardened | daemon/steps.py | medium |
| 14 | Prometheus metrics + HTTP server (start_http_server + /health) | daemon/metrics.py | low |
| 15 | Daemon main loop (calls metrics.record_*() directly) | daemon/main.py | medium |
| 16 | Dockerfile + requirements + smoke test | Dockerfile, docker/requirements.txt | medium |
| 17 | docker-compose.override.yml entry | docker-compose.override.yml | high (touches infra) |
| 18 | Modify SessionStart KB-briefing hook to read materialized file | hooks/session-start-kb-briefing.sh | medium |
| 19 | Modify UserPromptSubmit hook to read materialized file | hooks/user-prompt-kb-inject.sh | medium |
| 20 | Remove capture-guarantee Stop hook from settings.json | ~/.claude/settings.json | medium |
| 21 | Add .gitignore for `00-daemon-live-briefing.md` | aifactory + portage .gitignore | low |
| 22 | End-to-end integration verification | (manual) | medium |

**Deploy order:** Task 0 ships first (registry-only, can deploy independently). Tasks 1-16 build daemon code. 17 ships the container. 18-22 cut over hooks and verify.

**TDD:** Yes for Task 0 (registry tests) and Tasks 1-15 (daemon code). Each task starts with a failing test. Tasks 16-22 are infra/integration and don't follow strict TDD.

---

## Task 0: Registry fix — deferred-items sort + `last_surfaced_at`

**Why this is a prerequisite:** The session-start hook queries `GET /api/deferred-items?project_name=X&status=open&priority=high&limit=5`. The service layer orders by `created_at DESC`. Result: only the 5 most recently created high-priority items ever surface — anything older is structurally invisible, **even if it's blocking active work**. This is the root cause of the user's "lost deferred items" report. The daemon's Step 6 and Step 8 inherit this same query and would replicate the bug. Fix the registry first, then the daemon picks up the corrected behavior automatically.

**Files:**
- Modify: `registry/models.py` (add `last_surfaced_at` column to DeferredItem)
- Create: `registry/alembic/versions/<NNN>_add_deferred_last_surfaced.py`
- Modify: `registry/deferred_items_service.py` (add `sort` parameter, support `created_at_asc`)
- Modify: `registry/deferred_items_endpoints.py` (accept `sort` query param; new endpoint to bump `last_surfaced_at`)
- Modify: `registry/deferred_items_schemas.py` (add optional `sort`, `min_age_days`, `last_surfaced_before` filters)
- Modify: `registry/test_deferred_items.py` (new tests for sort and last_surfaced_at)

- [ ] **Step 1: Write failing test for sort=created_at_asc**

Add to `registry/test_deferred_items.py`:

```python
def test_list_deferred_items_sort_created_at_asc(client, session):
    """Items returned in ascending created_at order when sort=created_at_asc."""
    # Seed 3 items, oldest first
    from datetime import datetime, timezone, timedelta
    base = datetime.now(timezone.utc)
    for i, age_days in enumerate([30, 15, 1]):
        session.add(DeferredItem(
            title=f"item-{age_days}d-old",
            description="x", reason="x",
            category="other", project_name="dhg-ai-factory",
            priority="high", status="open",
            created_at=base - timedelta(days=age_days),
        ))
    session.commit()

    resp = client.get(
        "/api/deferred-items?project_name=dhg-ai-factory&status=open&priority=high&sort=created_at_asc&limit=5"
    )
    assert resp.status_code == 200
    titles = [item["title"] for item in resp.json()["deferred_items"]]
    assert titles == ["item-30d-old", "item-15d-old", "item-1d-old"]


def test_list_deferred_items_default_sort_unchanged(client, session):
    """Default sort remains created_at DESC for backward compat."""
    from datetime import datetime, timezone, timedelta
    base = datetime.now(timezone.utc)
    for age_days in [30, 1]:
        session.add(DeferredItem(
            title=f"item-{age_days}d",
            description="x", reason="x",
            category="other", project_name="dhg-ai-factory",
            priority="high", status="open",
            created_at=base - timedelta(days=age_days),
        ))
    session.commit()

    resp = client.get("/api/deferred-items?project_name=dhg-ai-factory&status=open&priority=high&limit=5")
    titles = [item["title"] for item in resp.json()["deferred_items"]]
    assert titles[0] == "item-1d"  # newest first (default)


def test_last_surfaced_at_starts_null(client, session):
    session.add(DeferredItem(
        title="fresh", description="x", reason="x",
        category="other", project_name="dhg-ai-factory",
        priority="high", status="open",
    ))
    session.commit()
    resp = client.get("/api/deferred-items?project_name=dhg-ai-factory&limit=1")
    assert resp.json()["deferred_items"][0]["last_surfaced_at"] is None


def test_bump_last_surfaced_at_endpoint(client, session):
    item = DeferredItem(
        title="surface-me", description="x", reason="x",
        category="other", project_name="dhg-ai-factory",
        priority="high", status="open",
    )
    session.add(item); session.commit()
    item_id = item.id

    resp = client.post(f"/api/deferred-items/{item_id}/surfaced")
    assert resp.status_code == 200

    resp = client.get(f"/api/deferred-items/{item_id}")
    assert resp.json()["last_surfaced_at"] is not None


def test_min_age_days_filter(client, session):
    from datetime import datetime, timezone, timedelta
    base = datetime.now(timezone.utc)
    session.add(DeferredItem(title="old", description="x", reason="x",
        category="other", project_name="dhg-ai-factory",
        priority="high", status="open",
        created_at=base - timedelta(days=30)))
    session.add(DeferredItem(title="new", description="x", reason="x",
        category="other", project_name="dhg-ai-factory",
        priority="high", status="open",
        created_at=base - timedelta(days=1)))
    session.commit()
    resp = client.get(
        "/api/deferred-items?project_name=dhg-ai-factory&status=open&min_age_days=7&limit=10"
    )
    titles = [i["title"] for i in resp.json()["deferred_items"]]
    assert "old" in titles
    assert "new" not in titles
```

Run: `cd ~/DHG/aifactory3.5/dhgaifactory3.5 && pytest registry/test_deferred_items.py -v -k "sort or last_surfaced or min_age"`
Expected: FAIL — column and parameters don't exist yet.

- [ ] **Step 2: Add migration**

Create `registry/alembic/versions/021_add_deferred_last_surfaced.py`:

```python
"""add last_surfaced_at to deferred_items

Revision ID: 021_add_deferred_last_surfaced
Revises: 020_add_agent_sessions_search
Create Date: 2026-05-28
"""
from alembic import op
import sqlalchemy as sa

revision = "021_add_deferred_last_surfaced"
down_revision = "020_add_agent_sessions_search"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("deferred_items",
        sa.Column("last_surfaced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_deferred_items_priority_status_age",
        "deferred_items",
        ["status", "priority", "created_at"],
    )


def downgrade():
    op.drop_index("ix_deferred_items_priority_status_age", table_name="deferred_items")
    op.drop_column("deferred_items", "last_surfaced_at")
```

Apply: `cd ~/DHG/aifactory3.5/dhgaifactory3.5 && docker compose exec dhg-registry-api alembic upgrade head`
Expected: migration applies cleanly. Verify with `docker compose exec dhg-registry-db psql -U dhg -d dhg_registry -c '\d deferred_items'` and confirm the new column exists.

- [ ] **Step 3: Add `last_surfaced_at` to model**

Edit `registry/models.py` — find the `DeferredItem` class and add:

```python
last_surfaced_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True, default=None
)
```

- [ ] **Step 4: Add sort + filter params to service layer**

Edit `registry/deferred_items_service.py` `list_deferred_items()`. Find the current `.order_by(DeferredItem.created_at.desc())` (around line 81) and replace the query-building logic to support a `sort` parameter:

```python
def list_deferred_items(
    db: Session,
    project_name: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "created_at_desc",
    min_age_days: int | None = None,
    last_surfaced_before_hours: int | None = None,
) -> list[DeferredItem]:
    query = db.query(DeferredItem)
    if project_name:
        query = query.filter(DeferredItem.project_name == project_name)
    if status:
        query = query.filter(DeferredItem.status == status)
    if priority:
        query = query.filter(DeferredItem.priority == priority)
    if category:
        query = query.filter(DeferredItem.category == category)
    if min_age_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=min_age_days)
        query = query.filter(DeferredItem.created_at <= cutoff)
    if last_surfaced_before_hours is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=last_surfaced_before_hours)
        query = query.filter(
            (DeferredItem.last_surfaced_at.is_(None)) |
            (DeferredItem.last_surfaced_at <= cutoff)
        )

    if sort == "created_at_asc":
        query = query.order_by(DeferredItem.created_at.asc())
    else:
        query = query.order_by(DeferredItem.created_at.desc())

    return query.offset(offset).limit(limit).all()


def mark_surfaced(db: Session, item_id: int) -> DeferredItem | None:
    item = db.query(DeferredItem).filter(DeferredItem.id == item_id).first()
    if item is None:
        return None
    item.last_surfaced_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(item)
    return item
```

- [ ] **Step 5: Wire endpoint changes**

Edit `registry/deferred_items_endpoints.py`. Add the new query params to the existing list endpoint:

```python
@router.get("", response_model=DeferredItemListResponse)
def list_items(
    project_name: str | None = Query(None),
    status: str | None = Query(None),
    priority: str | None = Query(None),
    category: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    sort: str = Query("created_at_desc", pattern="^(created_at_desc|created_at_asc)$"),
    min_age_days: int | None = Query(None, ge=0),
    last_surfaced_before_hours: int | None = Query(None, ge=0),
    db: Session = Depends(get_db),
):
    items = deferred_items_service.list_deferred_items(
        db, project_name=project_name, status=status, priority=priority,
        category=category, limit=limit, offset=offset, sort=sort,
        min_age_days=min_age_days,
        last_surfaced_before_hours=last_surfaced_before_hours,
    )
    return {"deferred_items": items}


@router.post("/{item_id}/surfaced", response_model=DeferredItemResponse)
def mark_surfaced_endpoint(item_id: int, db: Session = Depends(get_db)):
    item = deferred_items_service.mark_surfaced(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="deferred item not found")
    return item
```

- [ ] **Step 6: Run tests**

```bash
cd ~/DHG/aifactory3.5/dhgaifactory3.5
pytest registry/test_deferred_items.py -v
```
Expected: all PASS, including the 5 new sort/last-surfaced/min-age tests.

- [ ] **Step 7: Hot-reload registry (or rebuild)**

```bash
docker compose exec dhg-registry-api kill -HUP 1 2>/dev/null || docker compose restart dhg-registry-api
curl -s "http://10.0.0.251:8011/api/deferred-items?project_name=dhg-ai-factory&status=open&priority=high&sort=created_at_asc&limit=5" | jq '.deferred_items | length'
```
Expected: returns up to 5 items, oldest first.

- [ ] **Step 8: Commit**

```bash
cd ~/DHG/aifactory3.5/dhgaifactory3.5
git add registry/ docs/superpowers/plans/2026-05-28-memreg-daemon.md
git commit -m "feat(registry): add sort + last_surfaced_at to deferred items (fixes lost-items bug)"
```

**Rollback:** `alembic downgrade -1` + `git revert HEAD`. Existing queries without the new params continue to behave as before (default sort unchanged).

---

## Task 1: Daemon package + poller with tiktoken

**Files:**
- Create: `daemon/__init__.py`
- Create: `daemon/poller.py`
- Create: `tests/test_poller.py`
- Modify: `docker/requirements.txt`

- [ ] **Step 1: Add tiktoken to requirements**

Edit `docker/requirements.txt`:
```
httpx>=0.27,<1.0
tiktoken==0.7.0
prometheus_client>=0.21,<1.0
```

Run: `cd ~/DHG/dhg-memreg && pip install -r docker/requirements.txt`
Expected: tiktoken and prometheus_client install cleanly.

- [ ] **Step 2: Create empty daemon package**

Create `daemon/__init__.py` as an empty file.

Run: `touch ~/DHG/dhg-memreg/daemon/__init__.py`
Expected: file exists.

- [ ] **Step 3: Write failing poller tests**

Create `tests/test_poller.py`:

```python
"""Tests for daemon poller — token-based threshold detection with safe newline boundaries."""
import json
from pathlib import Path

import pytest

from daemon.poller import TranscriptPoller, SessionHit


def _write_entries(path: Path, count: int, text: str = "Hello world this is a test message with enough tokens"):
    with open(path, "w") as f:
        for _ in range(count):
            entry = {"type": "assistant", "message": {"content": text}}
            f.write(json.dumps(entry) + "\n")


def _append_entries(path: Path, count: int, text: str = "More content here for testing token accumulation"):
    with open(path, "a") as f:
        for _ in range(count):
            entry = {"type": "assistant", "message": {"content": text}}
            f.write(json.dumps(entry) + "\n")


@pytest.fixture
def projects_dir(tmp_path):
    slug_dir = tmp_path / "-home-user-project"
    slug_dir.mkdir()
    transcript = slug_dir / "abc-123.jsonl"
    _write_entries(transcript, 10)
    return tmp_path


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "state" / "sweep-state.json"


def test_first_run_records_baseline_no_fire(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=1)
    hits = poller.check()
    assert hits == []
    assert state_file.exists()


def test_growth_above_threshold_fires(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    poller.check()  # baseline
    transcript = list(projects_dir.glob("*/*.jsonl"))[0]
    _append_entries(transcript, 500)
    hits = poller.check()
    assert len(hits) == 1
    assert hits[0].session_id == "abc-123"
    assert hits[0].tokens_since_last >= 50


def test_growth_below_threshold_does_not_fire(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=999999)
    poller.check()
    transcript = list(projects_dir.glob("*/*.jsonl"))[0]
    _append_entries(transcript, 10)
    hits = poller.check()
    assert hits == []


def test_compaction_resets_baseline(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    poller.check()
    transcript = list(projects_dir.glob("*/*.jsonl"))[0]
    transcript.write_text('{"type":"assistant","message":{"content":"x"}}\n')
    hits = poller.check()
    assert hits == []


def test_state_persists_across_instances(projects_dir, state_file):
    p1 = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    p1.check()
    transcript = list(projects_dir.glob("*/*.jsonl"))[0]
    _append_entries(transcript, 500)
    p2 = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    hits = p2.check()
    assert len(hits) == 1


def test_restart_honors_existing_offsets(projects_dir, state_file):
    p1 = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=999999)
    p1.check()
    p2 = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=999999)
    hits = p2.check()
    assert hits == []


def test_skips_non_jsonl_files(tmp_path):
    slug = tmp_path / "-slug"
    slug.mkdir()
    (slug / "notes.txt").write_text("not a transcript")
    state = tmp_path / "state.json"
    poller = TranscriptPoller(projects_dir=tmp_path, state_file=state, threshold_tokens=1)
    assert poller.check() == []


def test_handles_malformed_json_lines(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    poller.check()
    transcript = list(projects_dir.glob("*/*.jsonl"))[0]
    with open(transcript, "a") as f:
        f.write("NOT VALID JSON\n")
        for _ in range(500):
            f.write(json.dumps({"type": "assistant", "message": {"content": "tokens here"}}) + "\n")
    hits = poller.check()
    assert len(hits) == 1


def test_stale_sessions_cleaned(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    poller.check()
    transcript = list(projects_dir.glob("*/*.jsonl"))[0]
    transcript.unlink()
    poller.check()
    state_data = json.loads(state_file.read_text())
    assert len(state_data) == 0


def test_atomic_state_write_survives_corrupt_temp(projects_dir, state_file):
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    poller.check()
    # State file should be valid JSON
    data = json.loads(state_file.read_text())
    assert isinstance(data, dict)


def test_corrupt_state_file_falls_back_to_first_run(projects_dir, state_file):
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text("NOT JSON")
    poller = TranscriptPoller(projects_dir=projects_dir, state_file=state_file, threshold_tokens=50)
    hits = poller.check()
    assert hits == []  # corrupt state → first-run no-fire
```

Run: `cd ~/DHG/dhg-memreg && pytest tests/test_poller.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'daemon.poller'`

- [ ] **Step 4: Implement poller**

Create `daemon/poller.py`:

```python
"""Poller — tracks JSONL transcript token growth and detects threshold crossings.

Token counting uses tiktoken cl100k_base encoding (closest local approximation to
Claude's tokenizer). DO NOT change without re-tuning the threshold.

Resumption is safe across restarts and crashes:
- Stored byte offset is always at a newline boundary (last successfully parsed line end)
- Mid-line writes by Claude Code are tolerated (we skip the partial line and resync at next \\n)
- State writes are atomic (tempfile + os.replace)
- Corrupt state falls back to first-run no-fire behavior
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import tiktoken

# cl100k_base is OpenAI's GPT-4 tokenizer — NOT Claude's. We use it as a local approximation
# because Anthropic doesn't publish a standalone Python tokenizer. For our purposes (a trigger
# threshold, not billing), the actual count doesn't need to match Claude exactly — we just need
# a stable, monotonic measure of activity. Threshold is configurable via SWEEP_THRESHOLD_TOKENS.
ENCODING = tiktoken.get_encoding("cl100k_base")


@dataclass
class SessionHit:
    session_id: str
    project_slug: str
    transcript_path: Path
    tokens_since_last: int


@dataclass
class _SessionState:
    byte_offset: int = 0
    tokens_accumulated: int = 0


class TranscriptPoller:
    """Polls JSONL transcripts, counts tokens incrementally, returns sessions above threshold."""

    def __init__(
        self,
        projects_dir: Path,
        state_file: Path,
        threshold_tokens: int = 100_000,
    ):
        self._projects_dir = Path(projects_dir)
        self._state_file = Path(state_file)
        self._threshold = threshold_tokens
        self._sessions: dict[str, _SessionState] = {}
        self._first_run = True
        self._load_state()

    def _load_state(self) -> None:
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text())
            if not isinstance(data, dict):
                return
            for key, val in data.items():
                self._sessions[key] = _SessionState(
                    byte_offset=int(val["byte_offset"]),
                    tokens_accumulated=int(val["tokens_accumulated"]),
                )
            self._first_run = False
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            # Corrupt state — fall back to first-run no-fire (don't crash)
            self._sessions = {}
            self._first_run = True

    def _save_state(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        data = {
            key: {"byte_offset": s.byte_offset, "tokens_accumulated": s.tokens_accumulated}
            for key, s in self._sessions.items()
        }
        fd, tmp = tempfile.mkstemp(dir=self._state_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
            os.replace(tmp, self._state_file)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    @staticmethod
    def _extract_text_from_line(line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        try:
            entry = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return ""
        if entry.get("type") not in ("human", "assistant"):
            return ""
        message = entry.get("message", {})
        if not isinstance(message, dict):
            return ""
        content = message.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return " ".join(parts)
        return ""

    def _count_new_tokens(self, path: Path, state: _SessionState) -> tuple[int, int]:
        """Read from last-known newline offset. Returns (new_tokens, new_safe_offset).

        Safe offset is always at a newline boundary so the next poll can resume
        cleanly even if Claude Code is mid-write.
        """
        try:
            file_size = path.stat().st_size
        except OSError:
            return 0, state.byte_offset

        if file_size < state.byte_offset:
            return 0, file_size  # compaction signal — caller handles
        if file_size == state.byte_offset:
            return 0, state.byte_offset

        new_tokens = 0
        safe_offset = state.byte_offset

        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(state.byte_offset)
                # Read the full file from offset, line by line.
                # Only advance safe_offset when we see a complete line (ending in \n).
                while True:
                    pos_before = f.tell()
                    line = f.readline()
                    if not line:
                        break
                    if not line.endswith("\n"):
                        # Partial line — don't advance safe_offset past it
                        break
                    text = self._extract_text_from_line(line)
                    if text:
                        try:
                            new_tokens += len(ENCODING.encode(text))
                        except Exception:
                            pass  # don't let tokenizer hiccups crash polling
                    safe_offset = f.tell()
        except OSError:
            return 0, state.byte_offset

        return new_tokens, safe_offset

    def check(self) -> list[SessionHit]:
        """Poll all session transcripts. Returns sessions that crossed the threshold."""
        hits: list[SessionHit] = []
        seen_keys: set[str] = set()

        if not self._projects_dir.exists():
            return []

        for slug_dir in self._projects_dir.iterdir():
            if not slug_dir.is_dir() or slug_dir.name.startswith("."):
                continue
            for transcript in slug_dir.glob("*.jsonl"):
                key = f"{slug_dir.name}/{transcript.stem}"
                seen_keys.add(key)

                try:
                    file_size = transcript.stat().st_size
                except OSError:
                    continue

                state = self._sessions.get(key)
                if state is None:
                    # New session — baseline only, no fire
                    self._sessions[key] = _SessionState(byte_offset=file_size, tokens_accumulated=0)
                    continue

                if file_size < state.byte_offset:
                    # Compaction — reset baseline, no fire
                    state.byte_offset = file_size
                    state.tokens_accumulated = 0
                    continue

                new_tokens, new_offset = self._count_new_tokens(transcript, state)
                state.byte_offset = new_offset
                state.tokens_accumulated += new_tokens

                if not self._first_run and state.tokens_accumulated >= self._threshold:
                    hits.append(SessionHit(
                        session_id=transcript.stem,
                        project_slug=slug_dir.name,
                        transcript_path=transcript,
                        tokens_since_last=state.tokens_accumulated,
                    ))
                    state.tokens_accumulated = 0

        # Clean stale sessions (transcript deleted)
        for key in list(self._sessions.keys()):
            if key not in seen_keys:
                del self._sessions[key]

        if self._first_run:
            self._first_run = False

        self._save_state()
        return hits
```

Run: `cd ~/DHG/dhg-memreg && pytest tests/test_poller.py -v`
Expected: PASS (all 11 tests).

- [ ] **Step 5: Commit**

```bash
cd ~/DHG/dhg-memreg
git add daemon/ tests/test_poller.py docker/requirements.txt
git commit -m "feat(daemon): add token-counting poller for transcript sweep triggers"
```

---

## Task 2: Dead-letter queue

**Files:**
- Create: `daemon/dlq.py`
- Create: `tests/test_dlq.py`

- [ ] **Step 1: Write failing DLQ tests**

Create `tests/test_dlq.py`:

```python
"""Tests for dead-letter queue — fcntl-locked append, retry, prune."""
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from daemon.dlq import DeadLetterQueue


@pytest.fixture
def dlq_file(tmp_path):
    return tmp_path / "dlq.jsonl"


@pytest.fixture
def dlq(dlq_file):
    return DeadLetterQueue(
        dlq_file=dlq_file,
        registry_url="http://test:8011",
        max_age_days=7,
        max_entries=5,
    )


def test_successful_post_does_not_enqueue(dlq, dlq_file):
    with patch("daemon.dlq.httpx") as mock_httpx:
        resp = MagicMock()
        resp.status_code = 201
        mock_httpx.post.return_value = resp
        mock_httpx.Timeout = MagicMock()
        result = dlq.post("post-insight", '{"tldr":"test"}')
    assert result is True
    assert not dlq_file.exists()


def test_failed_post_enqueues(dlq, dlq_file):
    with patch("daemon.dlq.httpx") as mock_httpx:
        mock_httpx.post.side_effect = Exception("connection refused")
        mock_httpx.Timeout = MagicMock()
        result = dlq.post("post-insight", '{"tldr":"test"}')
    assert result is False
    assert dlq_file.exists()
    assert dlq.depth() == 1


def test_non_2xx_response_enqueues(dlq, dlq_file):
    with patch("daemon.dlq.httpx") as mock_httpx:
        resp = MagicMock()
        resp.status_code = 422
        mock_httpx.post.return_value = resp
        mock_httpx.Timeout = MagicMock()
        result = dlq.post("post-insight", '{}')
    assert result is False
    assert dlq.depth() == 1


def test_retry_removes_successful(dlq, dlq_file):
    entry = {"endpoint": "post-insight", "payload": '{"x":1}', "timestamp": time.time(), "attempts": 1}
    dlq_file.write_text(json.dumps(entry) + "\n")
    with patch("daemon.dlq.httpx") as mock_httpx:
        resp = MagicMock()
        resp.status_code = 200
        mock_httpx.post.return_value = resp
        mock_httpx.Timeout = MagicMock()
        s, f, d = dlq.retry_all()
    assert s == 1 and f == 0
    assert dlq.depth() == 0


def test_retry_keeps_failed(dlq, dlq_file):
    entry = {"endpoint": "post-insight", "payload": '{"x":1}', "timestamp": time.time(), "attempts": 1}
    dlq_file.write_text(json.dumps(entry) + "\n")
    with patch("daemon.dlq.httpx") as mock_httpx:
        mock_httpx.post.side_effect = Exception("still down")
        mock_httpx.Timeout = MagicMock()
        s, f, d = dlq.retry_all()
    assert s == 0 and f == 1
    assert dlq.depth() == 1


def test_drops_old_entries(dlq, dlq_file):
    old = {"endpoint": "post-insight", "payload": "{}", "timestamp": time.time() - 8 * 86400, "attempts": 1}
    dlq_file.write_text(json.dumps(old) + "\n")
    s, f, d = dlq.retry_all()
    assert d == 1
    assert dlq.depth() == 0


def test_enforces_max_entries(dlq, dlq_file):
    lines = []
    for i in range(10):
        lines.append(json.dumps({
            "endpoint": "post-insight", "payload": f'{{"n":{i}}}',
            "timestamp": time.time(), "attempts": 1,
        }))
    dlq_file.write_text("\n".join(lines) + "\n")
    with patch("daemon.dlq.httpx") as mock_httpx:
        mock_httpx.post.side_effect = Exception("down")
        mock_httpx.Timeout = MagicMock()
        s, f, d = dlq.retry_all()
    assert d == 5
    assert dlq.depth() == 5


def test_skips_malformed_lines(dlq, dlq_file):
    valid = {"endpoint": "post-insight", "payload": "{}", "timestamp": time.time(), "attempts": 1}
    dlq_file.write_text("NOT JSON\n" + json.dumps(valid) + "\n")
    assert dlq.depth() == 1


def test_empty_file_returns_zeros(dlq):
    s, f, d = dlq.retry_all()
    assert (s, f, d) == (0, 0, 0)


def test_unknown_endpoint_drops_entry(dlq, dlq_file):
    bad = {"endpoint": "not-a-real-endpoint", "payload": "{}", "timestamp": time.time(), "attempts": 1}
    dlq_file.write_text(json.dumps(bad) + "\n")
    s, f, d = dlq.retry_all()
    assert d == 1
    assert dlq.depth() == 0
```

Run: `pytest tests/test_dlq.py -v`
Expected: FAIL — module not found.

- [ ] **Step 2: Implement DLQ**

Create `daemon/dlq.py`:

```python
"""Dead-letter queue for failed registry capture POSTs.

Persisted to ~/.claude/run/memreg-dlq.jsonl. Atomic appends via fcntl.flock.
Atomic rewrites via tempfile + os.replace.

Failed POSTs are enqueued. Each sweep retries all entries:
  - 2xx response → entry removed
  - Failure → entry kept (attempts++)
  - Age > max_age_days → entry dropped
  - Queue depth > max_entries → oldest entries dropped (FIFO)
"""
from __future__ import annotations

import fcntl
import json
import logging
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger("memreg.dlq")


# Import ENDPOINTS from the existing capture dispatcher — single source of truth.
# scripts/memreg_capture.py has no hyphens in the filename, so it's importable normally.
import sys
_SCRIPTS = Path(__file__).parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
from memreg_capture import ENDPOINTS  # noqa: E402


@dataclass
class DLQEntry:
    endpoint: str
    payload: str
    timestamp: float
    attempts: int


class DeadLetterQueue:
    def __init__(
        self,
        dlq_file: Path,
        registry_url: str = "http://10.0.0.251:8011",
        max_age_days: int = 7,
        max_entries: int = 1000,
    ):
        self._file = Path(dlq_file)
        self._registry_url = registry_url
        self._max_age = max_age_days * 86400
        self._max_entries = max_entries

    def _try_post(self, endpoint_command: str, payload: str) -> bool:
        if endpoint_command not in ENDPOINTS:
            logger.warning(f"Unknown endpoint command: {endpoint_command}")
            return False
        endpoint, _ = ENDPOINTS[endpoint_command]
        url = f"{self._registry_url}{endpoint}"
        try:
            resp = httpx.post(
                url,
                content=payload,
                headers={"Content-Type": "application/json"},
                timeout=httpx.Timeout(connect=2.0, read=5.0, write=5.0, pool=5.0),
            )
            return 200 <= resp.status_code < 300
        except Exception as e:
            logger.debug(f"POST {url} failed: {e}")
            return False

    def post(self, command: str, payload: str) -> bool:
        """Try to POST. On failure, enqueue. Returns True if POST succeeded."""
        if self._try_post(command, payload):
            return True
        self._append(DLQEntry(
            endpoint=command,
            payload=payload,
            timestamp=time.time(),
            attempts=1,
        ))
        return False

    def _append(self, entry: DLQEntry) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps({
            "endpoint": entry.endpoint,
            "payload": entry.payload,
            "timestamp": entry.timestamp,
            "attempts": entry.attempts,
        }) + "\n"
        with open(self._file, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(line)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    def retry_all(self) -> tuple[int, int, int]:
        """Retry every entry. Returns (succeeded, failed, dropped)."""
        if not self._file.exists():
            return 0, 0, 0

        entries = self._read_all()
        now = time.time()
        succeeded = 0
        failed = 0
        dropped = 0
        keep: list[DLQEntry] = []

        for entry in entries:
            if entry.endpoint not in ENDPOINTS:
                dropped += 1
                continue
            if now - entry.timestamp > self._max_age:
                dropped += 1
                continue
            if self._try_post(entry.endpoint, entry.payload):
                succeeded += 1
            else:
                entry.attempts += 1
                failed += 1
                keep.append(entry)

        if len(keep) > self._max_entries:
            dropped += len(keep) - self._max_entries
            keep = keep[-self._max_entries:]

        self._write_all(keep)
        return succeeded, failed, dropped

    def _read_all(self) -> list[DLQEntry]:
        entries: list[DLQEntry] = []
        if not self._file.exists():
            return entries
        with open(self._file, "r") as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(DLQEntry(
                            endpoint=data["endpoint"],
                            payload=data["payload"],
                            timestamp=float(data["timestamp"]),
                            attempts=int(data.get("attempts", 1)),
                        ))
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue  # skip malformed lines
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return entries

    def _write_all(self, entries: list[DLQEntry]) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    for entry in entries:
                        f.write(json.dumps({
                            "endpoint": entry.endpoint,
                            "payload": entry.payload,
                            "timestamp": entry.timestamp,
                            "attempts": entry.attempts,
                        }) + "\n")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
            os.replace(tmp, self._file)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def depth(self) -> int:
        return len(self._read_all())
```

Run: `pytest tests/test_dlq.py -v`
Expected: PASS (10 tests).

- [ ] **Step 3: Commit**

```bash
git add daemon/dlq.py tests/test_dlq.py
git commit -m "feat(daemon): add dead-letter queue for failed capture POSTs"
```

---

## Task 3: Sweep runner with threading timeouts

**Files:**
- Create: `daemon/sweep.py`
- Create: `tests/test_sweep.py`

- [ ] **Step 1: Write failing sweep tests**

Create `tests/test_sweep.py`:

```python
"""Tests for sweep runner — threading timeouts, two-tier context, no-stack guarantee."""
import threading
import time
from unittest.mock import MagicMock

import pytest

from daemon.sweep import SweepRunner, SweepConfig, StepDef, StepResult, SweepContext


def _ok_step(ctx: SweepContext) -> StepResult:
    return StepResult(name="ok", success=True, duration_seconds=0.01)


def _slow_step(ctx: SweepContext) -> StepResult:
    time.sleep(5)
    return StepResult(name="slow", success=True, duration_seconds=5.0)


def _failing_step(ctx: SweepContext) -> StepResult:
    raise RuntimeError("boom")


def _populating_step(ctx: SweepContext) -> StepResult:
    ctx.results["step1_data"] = ["a", "b"]
    return StepResult(name="populator", success=True, duration_seconds=0.01)


def _reading_step(ctx: SweepContext) -> StepResult:
    data = ctx.results.get("step1_data", [])
    return StepResult(name="reader", success=True, duration_seconds=0.01, detail=str(data))


@pytest.fixture
def config(tmp_path):
    return SweepConfig(
        registry_url="http://test:8011",
        projects_dir=tmp_path / "projects",
        dhg_root=tmp_path / "dhg",
        run_dir=tmp_path / "run",
        sweep_timeout=10,
    )


@pytest.fixture
def mock_dlq():
    return MagicMock()


def test_runs_all_steps(config, mock_dlq):
    steps = [StepDef(name="s1", fn=_ok_step, timeout=5), StepDef(name="s2", fn=_ok_step, timeout=5)]
    runner = SweepRunner(config, mock_dlq, steps)
    results = runner.run([])
    assert len(results) == 2
    assert all(r.success for r in results)


def test_step_timeout_does_not_block_others(config, mock_dlq):
    steps = [StepDef(name="slow", fn=_slow_step, timeout=1), StepDef(name="fast", fn=_ok_step, timeout=5)]
    runner = SweepRunner(config, mock_dlq, steps)
    results = runner.run([])
    assert not results[0].success
    assert "timeout" in results[0].detail
    assert results[1].success


def test_step_exception_does_not_block_others(config, mock_dlq):
    steps = [StepDef(name="fail", fn=_failing_step, timeout=5), StepDef(name="ok", fn=_ok_step, timeout=5)]
    runner = SweepRunner(config, mock_dlq, steps)
    results = runner.run([])
    assert not results[0].success
    assert "boom" in results[0].detail
    assert results[1].success


def test_sweep_timeout_abandons_remaining(config, mock_dlq):
    config.sweep_timeout = 2
    steps = [StepDef(name="slow", fn=_slow_step, timeout=3), StepDef(name="never", fn=_ok_step, timeout=5)]
    runner = SweepRunner(config, mock_dlq, steps)
    results = runner.run([])
    assert "timeout" in results[0].detail
    assert "skipped" in results[1].detail


def test_no_concurrent_sweeps(config, mock_dlq):
    steps = [StepDef(name="slow", fn=_slow_step, timeout=10)]
    runner = SweepRunner(config, mock_dlq, steps)
    results_2 = []

    def run1():
        runner.run([])

    def run2():
        time.sleep(0.1)
        results_2.extend(runner.run([]))

    t1 = threading.Thread(target=run1)
    t2 = threading.Thread(target=run2)
    t1.start()
    t2.start()
    t1.join(timeout=15)
    t2.join(timeout=15)
    assert results_2 == []


def test_context_results_pass_between_steps(config, mock_dlq):
    steps = [
        StepDef(name="populate", fn=_populating_step, timeout=5),
        StepDef(name="read", fn=_reading_step, timeout=5),
    ]
    runner = SweepRunner(config, mock_dlq, steps)
    results = runner.run([])
    assert results[1].detail == "['a', 'b']"


def test_running_flag_clears_on_exception(config, mock_dlq):
    steps = [StepDef(name="fail", fn=_failing_step, timeout=5)]
    runner = SweepRunner(config, mock_dlq, steps)
    runner.run([])
    assert not runner.is_running


def test_config_immutable_results_mutable(config, mock_dlq):
    """SweepConfig is frozen-ish (no field reassignment); ctx.results is the mutable bag."""
    steps = [StepDef(name="populate", fn=_populating_step, timeout=5)]
    runner = SweepRunner(config, mock_dlq, steps)
    runner.run([])
    # Config registry_url should still be the original
    assert config.registry_url == "http://test:8011"
```

Run: `pytest tests/test_sweep.py -v`
Expected: FAIL — module not found.

- [ ] **Step 2: Implement sweep runner**

Create `daemon/sweep.py`:

```python
"""Sweep runner — orchestrates 9 steps with per-step threading timeouts.

Design (advisor finding I3): two-tier context.
  - SweepConfig: immutable configuration (registry URL, paths, timeouts)
  - SweepContext.results: mutable dict that steps populate as they run

Threading (advisor finding I1): each step runs in a single-worker ThreadPoolExecutor
with future.result(timeout=N). This actually enforces timeouts on synchronous
function calls — asyncio.wait_for cannot interrupt blocking sync code.

No-stack guarantee: a flag prevents concurrent runs. If a sweep is already running,
a second run() call returns [] immediately.
"""
from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from daemon.dlq import DeadLetterQueue
from daemon.poller import SessionHit

logger = logging.getLogger("memreg.sweep")


@dataclass
class SweepConfig:
    """Immutable configuration. Same across all sweeps in a daemon lifetime."""
    registry_url: str = "http://10.0.0.251:8011"
    projects_dir: Path = field(default_factory=lambda: Path.home() / ".claude/projects")
    dhg_root: Path = field(default_factory=lambda: Path.home() / "DHG")
    run_dir: Path = field(default_factory=lambda: Path.home() / ".claude/run")
    sweep_timeout: int = 180


@dataclass
class SweepContext:
    """Passed to every step. config + dlq + sessions are immutable inputs;
    results is the mutable bag where steps publish outputs for downstream steps."""
    config: SweepConfig
    dlq: DeadLetterQueue
    sessions: list[SessionHit]
    results: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    name: str
    success: bool
    duration_seconds: float
    detail: str = ""


StepFn = Callable[[SweepContext], StepResult]


@dataclass
class StepDef:
    name: str
    fn: StepFn
    timeout: int


class SweepRunner:
    def __init__(self, config: SweepConfig, dlq: DeadLetterQueue, steps: list[StepDef]):
        self._config = config
        self._dlq = dlq
        self._steps = steps
        self._running = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._running

    def run(self, sessions: list[SessionHit]) -> list[StepResult]:
        with self._lock:
            if self._running:
                logger.warning("Sweep already running — skipping new trigger")
                return []
            self._running = True

        ctx = SweepContext(config=self._config, dlq=self._dlq, sessions=sessions, results={})
        results: list[StepResult] = []
        sweep_start = time.monotonic()

        try:
            for step_def in self._steps:
                elapsed = time.monotonic() - sweep_start
                if elapsed >= self._config.sweep_timeout:
                    logger.warning(f"Sweep budget ({self._config.sweep_timeout}s) exhausted — skipping {step_def.name}")
                    results.append(StepResult(
                        name=step_def.name, success=False,
                        duration_seconds=0,
                        detail="skipped: sweep timeout",
                    ))
                    continue

                remaining = self._config.sweep_timeout - elapsed
                timeout = min(step_def.timeout, remaining)
                results.append(self._run_step(step_def, ctx, timeout))
        finally:
            with self._lock:
                self._running = False

        total = time.monotonic() - sweep_start
        ok_count = sum(1 for r in results if r.success)
        logger.info(f"Sweep complete in {total:.1f}s — {ok_count}/{len(results)} steps succeeded")
        return results

    def run_with_ctx(self, sessions: list[SessionHit]) -> tuple[list[StepResult], SweepContext]:
        """Same as run() but returns the final SweepContext so the caller can read ctx.results."""
        with self._lock:
            if self._running:
                logger.warning("Sweep already running — skipping new trigger")
                return [], SweepContext(config=self._config, dlq=self._dlq, sessions=sessions, results={})
            self._running = True
        ctx = SweepContext(config=self._config, dlq=self._dlq, sessions=sessions, results={})
        results: list[StepResult] = []
        sweep_start = time.monotonic()
        try:
            for step_def in self._steps:
                elapsed = time.monotonic() - sweep_start
                if elapsed >= self._config.sweep_timeout:
                    results.append(StepResult(name=step_def.name, success=False, duration_seconds=0, detail="skipped: sweep timeout"))
                    continue
                remaining = self._config.sweep_timeout - elapsed
                results.append(self._run_step(step_def, ctx, min(step_def.timeout, remaining)))
        finally:
            with self._lock:
                self._running = False
        return results, ctx

    def _run_step(self, step_def: StepDef, ctx: SweepContext, timeout: float) -> StepResult:
        start = time.monotonic()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(step_def.fn, ctx)
            try:
                return future.result(timeout=timeout)
            except FuturesTimeout:
                logger.warning(f"Step {step_def.name} timed out after {timeout:.0f}s")
                future.cancel()
                return StepResult(
                    name=step_def.name, success=False,
                    duration_seconds=time.monotonic() - start,
                    detail=f"timeout after {timeout:.0f}s",
                )
            except Exception as e:
                logger.exception(f"Step {step_def.name} failed")
                return StepResult(
                    name=step_def.name, success=False,
                    duration_seconds=time.monotonic() - start,
                    detail=str(e),
                )
```

Run: `pytest tests/test_sweep.py -v`
Expected: PASS (8 tests).

- [ ] **Step 3: Commit**

```bash
git add daemon/sweep.py tests/test_sweep.py
git commit -m "feat(daemon): add sweep runner with threading-based step timeouts"
```

---

## Task 4: Refactor capture-guarantee.py for import

**Files:**
- Modify: `hooks/capture-guarantee.py`
- Modify: `tests/test_hooks.py` (if needed for new function signatures)

**Goal:** Extract the pure parsing and payload-building logic from `capture-guarantee.py` into importable functions so the daemon Step 1 can call them without shelling out.

Current `capture-guarantee.py` has module-level state (`DRY_RUN`, `SESSION_ID_OVERRIDE`, `LOG_FILE`, `SCRIPTS_DIR`) and `main()` does everything. Refactor to:
- Keep `parse_transcript(transcript_path)` — already pure (operates on file).
- Keep all `build_*_payload()` functions — already pure.
- Add `extract_capture_payloads(transcript_path, session_id, dedup_state) -> list[tuple[str, str]]` returning `[(command_name, payload_json)]` pairs.
- Keep `main()` for backward compatibility (CLI use unchanged).
- Replace `derive_project_name()` call sites with a `project_name` parameter so daemon can pass it in.

- [ ] **Step 1: Run existing tests to baseline**

```bash
cd ~/DHG/dhg-memreg
pytest tests/test_hooks.py -v
```
Expected: existing tests PASS.

- [ ] **Step 2: Add project_name parameter to build_*_payload functions**

Each `build_*_payload` function in `hooks/capture-guarantee.py` currently calls `derive_project_name()` internally. Add an optional `project_name` parameter to each so the daemon can pass a per-sweep project explicitly. This eliminates the need for `globals()` monkey-patching.

Edit each `build_*_payload` function — change the signature and replace the inline call:

```python
def build_insight_payload(insight_text: str, project_name: str | None = None) -> str:
    project_name = project_name or derive_project_name()
    # ... rest unchanged, replace any derive_project_name() calls with project_name
```

Do the same for: `build_ship_session_payload`, `build_decision_payload`, `build_deferred_payload`, `build_correction_payload`, `build_bug_fix_payload`. Each gains a `project_name: str | None = None` parameter; first line of each becomes `project_name = project_name or derive_project_name()`.

This keeps the Stop-hook `main()` calling these functions unchanged (project_name=None → falls back to derive). The daemon passes it explicitly.

- [ ] **Step 3: Add extract_capture_payloads function (no globals())**

Edit `hooks/capture-guarantee.py` — add this function above `main()` (around line 505):

```python
def extract_capture_payloads(
    transcript_path: "Path",
    session_id: str,
    dedup_state: dict | None = None,
    project_name: str | None = None,
) -> list[tuple[str, str]]:
    """Pure function: parse a transcript, return list of (command, payload_json) for missed captures.

    This is the daemon-friendly entry point. The Stop-hook main() wraps this with
    subprocess.Popen calls; the daemon wraps it with dlq.post() calls.

    Args:
        transcript_path: Path to .jsonl session transcript
        session_id: session ID (for dedup state file naming)
        dedup_state: prior counts of {insights, ship, decisions, deferred, corrections, bug_fixes}
        project_name: project to attribute payloads to (defaults to derive_project_name())

    Returns:
        List of (command_name, payload_json) tuples.
    """
    dedup_state = dedup_state or {}
    if project_name is None:
        project_name = derive_project_name()

    result = parse_transcript(transcript_path)
    if not result.get("valid"):
        return []

    payloads: list[tuple[str, str]] = []

    insights_found = result["insights_found"]
    missed = len(insights_found) - (result["post_insight_count"] + dedup_state.get("insights", 0))
    if missed > 0:
        for insight in insights_found[-missed:]:
            payloads.append(("post-insight", build_insight_payload(insight, project_name=project_name)))

    if (result["ship_session_complete"] and not result["post_ship_session_called"]
            and not dedup_state.get("ship", 0) and result["ship_state_content"]):
        payloads.append(("post-ship-session", build_ship_session_payload(
            result["ship_state_content"], project_name=project_name)))

    decisions_found = result["decisions_found"]
    missed = len(decisions_found) - (result["post_decision_count"] + dedup_state.get("decisions", 0))
    if missed > 0:
        for decision in decisions_found[-missed:]:
            p = build_decision_payload(decision, project_name=project_name)
            if p:
                payloads.append(("post-decision-logs", p))

    deferred_items: list[str] = []
    if result["ship_state_content"]:
        deferred_items = extract_deferred_items(result["ship_state_content"])
    missed = len(deferred_items) - (result["post_deferred_count"] + dedup_state.get("deferred", 0))
    feature_name = ""
    if result["ship_state_content"]:
        fm = re.search(r"^feature:\s*(.+)$", result["ship_state_content"], re.MULTILINE)
        if fm:
            feature_name = fm.group(1).strip()
    if missed > 0:
        for item in deferred_items[-missed:]:
            payloads.append(("post-deferred-items", build_deferred_payload(
                item, feature_name, project_name=project_name)))

    corrections_found = result["corrections_found"]
    missed = len(corrections_found) - (result["post_correction_count"] + dedup_state.get("corrections", 0))
    if missed > 0:
        for corr in corrections_found[-missed:]:
            payloads.append(("post-correction", build_correction_payload(corr, project_name=project_name)))

    bug_fixes_found = result["bug_fixes_found"]
    missed = len(bug_fixes_found) - (result["post_bug_fix_count"] + dedup_state.get("bug_fixes", 0))
    if missed > 0:
        for fix in bug_fixes_found[-missed:]:
            payloads.append(("post-bug-fixes", build_bug_fix_payload(fix, project_name=project_name)))

    return payloads
```

No `globals()` mutation. Thread-safe by construction.

- [ ] **Step 3: Add test for extract_capture_payloads**

Add to `tests/test_hooks.py`:

```python
def test_extract_capture_payloads_returns_command_payload_pairs(tmp_path):
    """The daemon-friendly entry point should return [(command, json), ...]."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "capture_guarantee", Path(__file__).parent.parent / "hooks" / "capture-guarantee.py"
    )
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    # Empty transcript → no payloads
    empty = tmp_path / "empty.jsonl"
    empty.write_text("")
    assert m.extract_capture_payloads(empty, "test-session", {}) == []
```

Run: `pytest tests/test_hooks.py -v`
Expected: existing + new tests PASS.

- [ ] **Step 4: Commit**

```bash
git add hooks/capture-guarantee.py tests/test_hooks.py
git commit -m "refactor(hooks): extract daemon-importable extract_capture_payloads from capture-guarantee"
```

---

## Task 5: Steps 1 & 2 — Capture-guarantee + DLQ retry

**Files:**
- Create: `daemon/steps.py` (initial file)
- Create: `tests/test_steps.py`

- [ ] **Step 1: Write failing test for step 1**

Create `tests/test_steps.py`:

```python
"""Tests for daemon sweep steps."""
import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from daemon.dlq import DeadLetterQueue
from daemon.poller import SessionHit
from daemon.sweep import SweepConfig, SweepContext
from daemon.steps import step_capture_guarantee, step_dlq_retry


@pytest.fixture
def ctx(tmp_path):
    config = SweepConfig(
        registry_url="http://test:8011",
        projects_dir=tmp_path / "projects",
        dhg_root=tmp_path / "dhg",
        run_dir=tmp_path / "run",
    )
    config.run_dir.mkdir(parents=True, exist_ok=True)
    dlq = DeadLetterQueue(dlq_file=config.run_dir / "dlq.jsonl", registry_url=config.registry_url)
    return SweepContext(config=config, dlq=dlq, sessions=[], results={})


def test_step_capture_guarantee_no_sessions(ctx):
    result = step_capture_guarantee(ctx)
    assert result.success
    assert "0 payloads" in result.detail


def test_step_capture_guarantee_calls_dlq_post(ctx, tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("")  # empty
    ctx.sessions = [SessionHit(
        session_id="test-1", project_slug="-tmp-x",
        transcript_path=transcript, tokens_since_last=100000,
    )]
    with patch.object(ctx.dlq, "post", return_value=True) as mock_post:
        result = step_capture_guarantee(ctx)
    assert result.success
    # Empty transcript → no payloads → no dlq.post calls
    assert mock_post.call_count == 0
```

Run: `pytest tests/test_steps.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement step 1**

Create `daemon/steps.py`:

```python
"""Sweep step implementations.

Each step is a synchronous function that takes a SweepContext and returns a StepResult.
Steps are run with per-step threading timeouts by SweepRunner — they don't need to
manage their own timeouts.
"""
from __future__ import annotations

import importlib.util
import json
import logging
import time
from pathlib import Path

from daemon.sweep import SweepContext, StepResult

logger = logging.getLogger("memreg.steps")


# Lazy import of capture-guarantee since the filename has a hyphen
_CAPTURE_GUARANTEE_MODULE = None


def _load_capture_guarantee():
    global _CAPTURE_GUARANTEE_MODULE
    if _CAPTURE_GUARANTEE_MODULE is not None:
        return _CAPTURE_GUARANTEE_MODULE
    path = Path(__file__).parent.parent / "hooks" / "capture-guarantee.py"
    spec = importlib.util.spec_from_file_location("capture_guarantee", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _CAPTURE_GUARANTEE_MODULE = m
    return m


def _dedup_path(run_dir: Path, session_id: str) -> Path:
    return run_dir / f"guarantee-posted-{session_id}"


def _load_dedup(run_dir: Path, session_id: str) -> dict:
    path = _dedup_path(run_dir, session_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_dedup(run_dir: Path, session_id: str, state: dict) -> None:
    path = _dedup_path(run_dir, session_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state))
    except OSError as e:
        logger.warning(f"Failed to save dedup state for {session_id}: {e}")


def _project_name_from_slug(slug: str) -> str:
    """Map ~/.claude/projects/<slug> back to a project_name."""
    if "aifactory" in slug:
        return "dhg-ai-factory"
    if "portage" in slug:
        return "portage"
    if "c2l-vault" in slug:
        return "c2l-vault"
    if "claude-code-tresor" in slug:
        return "claude-code-tresor"
    if "Digital-Harmony-Studio" in slug or "digital-harmony-studio" in slug:
        return "digital-harmony-studio"
    return slug.lstrip("-").split("-")[-1] or "unknown"


def step_capture_guarantee(ctx: SweepContext) -> StepResult:
    """Step 1: For each triggered session, scan transcript for missed captures and post via DLQ."""
    start = time.monotonic()
    if not ctx.sessions:
        return StepResult(name="capture_guarantee", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="0 sessions, 0 payloads")

    cg = _load_capture_guarantee()
    total_payloads = 0
    total_posted = 0
    total_dlq = 0

    for session in ctx.sessions:
        project_name = _project_name_from_slug(session.project_slug)
        dedup = _load_dedup(ctx.config.run_dir, session.session_id)

        try:
            payloads = cg.extract_capture_payloads(
                session.transcript_path,
                session.session_id,
                dedup_state=dedup,
                project_name=project_name,
            )
        except Exception as e:
            logger.exception(f"extract_capture_payloads failed for {session.session_id}")
            continue

        counters = {"insights": 0, "ship": 0, "decisions": 0, "deferred": 0, "corrections": 0, "bug_fixes": 0}
        for command, payload in payloads:
            total_payloads += 1
            if ctx.dlq.post(command, payload):
                total_posted += 1
            else:
                total_dlq += 1
            # Update dedup counter for the kind we just posted
            if command == "post-insight":
                counters["insights"] += 1
            elif command == "post-ship-session":
                counters["ship"] += 1
            elif command == "post-decision-logs":
                counters["decisions"] += 1
            elif command == "post-deferred-items":
                counters["deferred"] += 1
            elif command == "post-correction":
                counters["corrections"] += 1
            elif command == "post-bug-fixes":
                counters["bug_fixes"] += 1

        for k, v in counters.items():
            dedup[k] = dedup.get(k, 0) + v
        _save_dedup(ctx.config.run_dir, session.session_id, dedup)

    ctx.results["captures_posted"] = total_posted
    ctx.results["captures_dlq"] = total_dlq

    return StepResult(
        name="capture_guarantee", success=True,
        duration_seconds=time.monotonic() - start,
        detail=f"{len(ctx.sessions)} sessions, {total_payloads} payloads, {total_posted} posted, {total_dlq} dlq",
    )


def step_dlq_retry(ctx: SweepContext) -> StepResult:
    """Step 2: Retry every entry in the DLQ."""
    start = time.monotonic()
    succeeded, failed, dropped = ctx.dlq.retry_all()
    ctx.results["dlq_retried"] = succeeded
    ctx.results["dlq_failed"] = failed
    ctx.results["dlq_dropped"] = dropped
    return StepResult(
        name="dlq_retry", success=True,
        duration_seconds=time.monotonic() - start,
        detail=f"retried={succeeded} failed={failed} dropped={dropped}",
    )
```

Run: `pytest tests/test_steps.py -v -k test_step_capture_guarantee`
Expected: PASS.

- [ ] **Step 3: Add DLQ retry test (Step 2's implementation already lives in `step_dlq_retry` above)**

Append to `tests/test_steps.py`:

```python
def test_step_dlq_retry_calls_dlq_retry_all(ctx):
    with patch.object(ctx.dlq, "retry_all", return_value=(3, 1, 2)) as mock_retry:
        result = step_dlq_retry(ctx)
    assert result.success
    assert "retried=3" in result.detail
    assert ctx.results["dlq_retried"] == 3
    assert ctx.results["dlq_failed"] == 1
    assert ctx.results["dlq_dropped"] == 2
```

Run: `pytest tests/test_steps.py -v -k "test_step_capture_guarantee or test_step_dlq_retry"`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add daemon/steps.py tests/test_steps.py
git commit -m "feat(daemon): add Steps 1 + 2 (capture-guarantee, DLQ retry)"
```

---

## Task 6: Mtime tracker for ingestion

**Files:**
- Create: `daemon/mtime_tracker.py`
- Create: `tests/test_mtime_tracker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mtime_tracker.py`:

```python
"""Tests for mtime tracker — detect changed files between sweeps."""
import json
import os
import time
from pathlib import Path

import pytest

from daemon.mtime_tracker import MtimeTracker


@pytest.fixture
def state_file(tmp_path):
    return tmp_path / "mtime.json"


def test_first_run_records_baseline_no_changes(tmp_path, state_file):
    (tmp_path / "a.md").write_text("hello")
    tracker = MtimeTracker(state_file=state_file)
    changed = tracker.scan({"memory": [tmp_path]})
    assert changed == {"memory": []}


def test_new_file_detected_after_baseline(tmp_path, state_file):
    (tmp_path / "a.md").write_text("hello")
    tracker = MtimeTracker(state_file=state_file)
    tracker.scan({"memory": [tmp_path]})
    (tmp_path / "b.md").write_text("new")
    changed = tracker.scan({"memory": [tmp_path]})
    assert len(changed["memory"]) == 1
    assert changed["memory"][0].name == "b.md"


def test_modified_file_detected(tmp_path, state_file):
    f = tmp_path / "a.md"
    f.write_text("hello")
    tracker = MtimeTracker(state_file=state_file)
    tracker.scan({"memory": [tmp_path]})
    time.sleep(0.05)
    f.write_text("modified")
    os.utime(f, (time.time(), time.time()))
    changed = tracker.scan({"memory": [tmp_path]})
    assert len(changed["memory"]) == 1


def test_unchanged_file_not_in_results(tmp_path, state_file):
    (tmp_path / "a.md").write_text("hello")
    tracker = MtimeTracker(state_file=state_file)
    tracker.scan({"memory": [tmp_path]})
    changed = tracker.scan({"memory": [tmp_path]})
    assert changed["memory"] == []


def test_state_persists(tmp_path, state_file):
    (tmp_path / "a.md").write_text("hello")
    MtimeTracker(state_file=state_file).scan({"memory": [tmp_path]})
    t2 = MtimeTracker(state_file=state_file)
    changed = t2.scan({"memory": [tmp_path]})
    assert changed["memory"] == []  # state honored


def test_multiple_categories(tmp_path, state_file):
    a = tmp_path / "memory"; a.mkdir()
    b = tmp_path / "claude_md"; b.mkdir()
    (a / "x.md").write_text("a")
    (b / "CLAUDE.md").write_text("b")
    tracker = MtimeTracker(state_file=state_file)
    tracker.scan({"memory": [a], "claude_md": [b]})
    (a / "x.md").write_text("a2")
    os.utime(a / "x.md", (time.time() + 1, time.time() + 1))
    changed = tracker.scan({"memory": [a], "claude_md": [b]})
    assert len(changed["memory"]) == 1
    assert changed["claude_md"] == []
```

Run: `pytest tests/test_mtime_tracker.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement mtime tracker**

Create `daemon/mtime_tracker.py`:

```python
"""Mtime tracker — detect which files have changed since the last sweep.

State file holds {category: {filepath: mtime}}. First-run records all mtimes
as baseline without reporting changes (avoids mass-reingest on daemon start).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


class MtimeTracker:
    def __init__(self, state_file: Path):
        self._state_file = Path(state_file)
        self._state: dict[str, dict[str, float]] = {}
        self._first_run = True
        self._load()

    def _load(self) -> None:
        if not self._state_file.exists():
            return
        try:
            data = json.loads(self._state_file.read_text())
            if isinstance(data, dict):
                self._state = {k: dict(v) for k, v in data.items() if isinstance(v, dict)}
                self._first_run = False
        except (json.JSONDecodeError, OSError):
            self._state = {}
            self._first_run = True

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self._state_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(self._state, f)
            os.replace(tmp, self._state_file)
        except OSError:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def scan(self, categories: dict[str, list[Path]]) -> dict[str, list[Path]]:
        """Scan a set of directory roots per category. Returns changed files per category.

        categories = {"memory": [Path1, Path2], "claude_md": [Path3]}
        On first run, records all mtimes but returns empty lists (no fire).
        """
        changed: dict[str, list[Path]] = {cat: [] for cat in categories}

        for cat, roots in categories.items():
            current: dict[str, float] = {}
            for root in roots:
                if not root.exists():
                    continue
                # Glob *.md only — both memory files and CLAUDE.md fit
                if root.is_file():
                    files = [root] if root.suffix == ".md" else []
                else:
                    files = list(root.glob("*.md"))
                for f in files:
                    try:
                        mtime = f.stat().st_mtime
                    except OSError:
                        continue
                    key = str(f.resolve())
                    current[key] = mtime
                    if not self._first_run:
                        prev = self._state.get(cat, {}).get(key)
                        if prev is None or mtime > prev:
                            changed[cat].append(f)
            self._state[cat] = current

        if self._first_run:
            self._first_run = False
            # Returned changed is already empty lists; just save baseline and return
            self._save()
            return {cat: [] for cat in categories}

        self._save()
        return changed
```

Run: `pytest tests/test_mtime_tracker.py -v`
Expected: PASS (6 tests).

- [ ] **Step 3: Commit**

```bash
git add daemon/mtime_tracker.py tests/test_mtime_tracker.py
git commit -m "feat(daemon): add mtime tracker for ingestion change detection"
```

---

## Task 7: Add `argv=None` parameter to ingest `main()` functions

**Why:** The daemon needs to call these scripts from Python without mutating `sys.argv` (which is process-global and would race with anything else inspecting argv). `argparse` already supports this — `parser.parse_args(argv)` accepts a list. The change is one-line per script.

**Files:**
- Modify: `scripts/ingest-memory-files.py`
- Modify: `scripts/ingest-claude-md.py`
- Modify: `tests/test_ingest_memory_files.py`
- Modify: `tests/test_ingest_claude_md.py`

- [ ] **Step 1: Add argv parameter to ingest-memory-files.py**

Edit `scripts/ingest-memory-files.py`. Find `def main():` (around line 299):

```python
def main(argv=None):
    global REGISTRY_URL, MEMORY_DIR, PROJECT_NAME, DRY_RUN
    parser = argparse.ArgumentParser(...)
    # ... unchanged
    args = parser.parse_args(argv)  # was: parser.parse_args()
    # ... rest unchanged
```

- [ ] **Step 2: Add argv parameter to ingest-claude-md.py**

Edit `scripts/ingest-claude-md.py`. Find `def main():` (around line 109):

```python
def main(argv=None):
    global REGISTRY_URL, DHG_ROOT, BATCH_NAME, DRY_RUN
    parser = argparse.ArgumentParser(...)
    # ... unchanged
    args = parser.parse_args(argv)  # was: parser.parse_args()
    # ... rest unchanged
```

- [ ] **Step 3: Add tests asserting argv parameter works**

Append to `tests/test_ingest_memory_files.py`:

```python
def test_main_accepts_argv_parameter(monkeypatch, tmp_path):
    """main(argv=[...]) parses without touching sys.argv."""
    mem = tmp_path / "memory"
    mem.mkdir()
    (mem / "test.md").write_text("---\ntype: feedback\nname: test\n---\nbody")

    original_argv = sys.argv[:]
    main(argv=["--project", "test-project", "--memory-dir", str(mem), "--dry-run"])
    assert sys.argv == original_argv  # unchanged
```

Same pattern for `tests/test_ingest_claude_md.py`.

- [ ] **Step 4: Run tests**

```bash
cd ~/DHG/dhg-memreg
pytest tests/test_ingest_memory_files.py tests/test_ingest_claude_md.py -v
```
Expected: all PASS (existing tests + 2 new).

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest-memory-files.py scripts/ingest-claude-md.py tests/test_ingest_memory_files.py tests/test_ingest_claude_md.py
git commit -m "refactor(scripts): add argv= parameter to ingest main() functions"
```

---

## Task 8: Step 3 — Ingest memory files

**Files:**
- Modify: `daemon/steps.py`
- Modify: `tests/test_steps.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_steps.py`:

```python
def test_step_ingest_memory_first_run_no_op(ctx, tmp_path):
    from daemon.steps import step_ingest_memory
    projects = tmp_path / "projects"
    slug = projects / "-home-user-aifactory"
    memory_dir = slug / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "test.md").write_text("---\ntype: feedback\nname: test\n---\nbody")
    ctx.config.projects_dir = projects
    result = step_ingest_memory(ctx)
    assert result.success
    assert "0 ingested" in result.detail or "no changes" in result.detail


def test_step_ingest_memory_skips_when_no_projects(ctx):
    from daemon.steps import step_ingest_memory
    result = step_ingest_memory(ctx)
    assert result.success
```

- [ ] **Step 2: Add step_ingest_memory to daemon/steps.py**

Append to `daemon/steps.py`:

```python
# === Step 3: Ingest memory files ============================================

# Lazy import for ingest-memory-files.py (filename has hyphens)
_INGEST_MEMORY_MODULE = None


def _load_ingest_memory():
    global _INGEST_MEMORY_MODULE
    if _INGEST_MEMORY_MODULE is not None:
        return _INGEST_MEMORY_MODULE
    path = Path(__file__).parent.parent / "scripts" / "ingest-memory-files.py"
    spec = importlib.util.spec_from_file_location("ingest_memory_files", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _INGEST_MEMORY_MODULE = m
    return m


def step_ingest_memory(ctx: SweepContext) -> StepResult:
    """Step 3: Re-ingest memory files whose mtime changed since last sweep."""
    from daemon.mtime_tracker import MtimeTracker

    start = time.monotonic()
    tracker = MtimeTracker(state_file=ctx.config.run_dir / "memreg-mtime-state.json")

    # Collect memory directories per project slug
    memory_dirs: dict[str, Path] = {}
    if ctx.config.projects_dir.exists():
        for slug_dir in ctx.config.projects_dir.iterdir():
            if not slug_dir.is_dir():
                continue
            mem = slug_dir / "memory"
            if mem.exists() and mem.is_dir():
                memory_dirs[slug_dir.name] = mem

    if not memory_dirs:
        return StepResult(name="ingest_memory", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="no project memory dirs found")

    # Scan all in one mtime category, then group changed back to project
    all_dirs = list(memory_dirs.values())
    changed_by_cat = tracker.scan({"memory": all_dirs})
    changed_files = changed_by_cat.get("memory", [])

    if not changed_files:
        return StepResult(name="ingest_memory", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="0 ingested (no changes)")

    # Group changed files by their project slug, then call ingest per project
    ingest = _load_ingest_memory()
    total_ingested = 0
    # I3 fix: BATCH_DATE is set at module import time. Refresh it before each call
    # so documents are tagged with the current date, not the daemon start date.
    from datetime import datetime
    ingest.BATCH_DATE = datetime.now().strftime("%Y-%m-%d")

    for slug, mem_dir in memory_dirs.items():
        project_changes = [f for f in changed_files if str(f).startswith(str(mem_dir))]
        if not project_changes:
            continue
        project_name = _project_name_from_slug(slug)
        # Pass argv explicitly — no sys.argv mutation (C3 fix)
        argv = [
            "--project", project_name,
            "--memory-dir", str(mem_dir),
            "--registry-url", ctx.config.registry_url,
        ]
        try:
            ingest.main(argv=argv)
            total_ingested += len(project_changes)
        except SystemExit:
            pass
        except Exception as e:
            logger.exception(f"ingest-memory-files failed for {project_name}: {e}")

    ctx.results["memory_files_ingested"] = total_ingested
    return StepResult(name="ingest_memory", success=True,
                      duration_seconds=time.monotonic() - start,
                      detail=f"{total_ingested} ingested across {len(memory_dirs)} projects")
```

Run: `pytest tests/test_steps.py -v -k test_step_ingest_memory`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add daemon/steps.py tests/test_steps.py
git commit -m "feat(daemon): add Step 3 (ingest memory files) via mtime tracking"
```

---

## Task 9: Step 4 — Ingest CLAUDE.md files

**Files:**
- Modify: `daemon/steps.py`
- Modify: `tests/test_steps.py`
- Modify: `scripts/ingest-claude-md.py` (advisor finding C1 — sys.path hack)

- [ ] **Step 1: Fix sys.path hack in ingest-claude-md.py**

Edit `scripts/ingest-claude-md.py` lines 42-44:

Replace:
```python
REGISTRY_SRC = Path.home() / "DHG/aifactory3.5/dhgaifactory3.5/registry"
sys.path.insert(0, str(REGISTRY_SRC))
from doc_ingest import chunk_markdown
```

With:
```python
# Resolve registry path. In the dhg-memreg container, ~/DHG is volume-mounted at
# /home/swebber64/DHG, so Path.home() returns /root inside the container — we
# must use an absolute path or honor the env var.
_REGISTRY_SRC_DEFAULT = "/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry"
REGISTRY_SRC = Path(os.environ.get("REGISTRY_SRC_PATH", _REGISTRY_SRC_DEFAULT))
if not REGISTRY_SRC.exists():
    # Fall back to Path.home() for non-container use
    REGISTRY_SRC = Path.home() / "DHG/aifactory3.5/dhgaifactory3.5/registry"
sys.path.insert(0, str(REGISTRY_SRC))
from doc_ingest import chunk_markdown
```

Run: `pytest tests/test_ingest_claude_md.py -v`
Expected: existing tests still PASS.

- [ ] **Step 2: Add step_ingest_claude_md test**

Append to `tests/test_steps.py`:

```python
def test_step_ingest_claude_md_first_run_no_op(ctx, tmp_path):
    from daemon.steps import step_ingest_claude_md
    project = tmp_path / "dhg" / "aifactory3.5" / "dhgaifactory3.5"
    project.mkdir(parents=True)
    (project / "CLAUDE.md").write_text("# Test")
    ctx.config.dhg_root = tmp_path / "dhg"
    result = step_ingest_claude_md(ctx)
    assert result.success
```

- [ ] **Step 3: Implement step 4**

Append to `daemon/steps.py`:

```python
# === Step 4: Ingest CLAUDE.md files =========================================

_INGEST_CLAUDE_MD_MODULE = None

# Project slug → CLAUDE.md path mapping (relative to DHG_ROOT)
_CLAUDE_MD_PROJECTS = {
    "dhg-ai-factory": "aifactory3.5/dhgaifactory3.5",
    "portage": "portage",
    "c2l-vault": "c2l-vault",
    "claude-code-tresor": "claude-code-tresor",
    "digital-harmony-studio": "Digital-Harmony-Studio-v1",
}


def _load_ingest_claude_md():
    global _INGEST_CLAUDE_MD_MODULE
    if _INGEST_CLAUDE_MD_MODULE is not None:
        return _INGEST_CLAUDE_MD_MODULE
    path = Path(__file__).parent.parent / "scripts" / "ingest-claude-md.py"
    spec = importlib.util.spec_from_file_location("ingest_claude_md", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    _INGEST_CLAUDE_MD_MODULE = m
    return m


def step_ingest_claude_md(ctx: SweepContext) -> StepResult:
    """Step 4: Re-ingest CLAUDE.md files whose mtime changed since last sweep."""
    from daemon.mtime_tracker import MtimeTracker

    start = time.monotonic()
    tracker = MtimeTracker(state_file=ctx.config.run_dir / "memreg-mtime-state.json")

    claude_md_files: list[Path] = []
    for _project, rel in _CLAUDE_MD_PROJECTS.items():
        p = ctx.config.dhg_root / rel / "CLAUDE.md"
        if p.exists():
            claude_md_files.append(p)

    if not claude_md_files:
        return StepResult(name="ingest_claude_md", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="no CLAUDE.md files found")

    changed = tracker.scan({"claude_md": claude_md_files}).get("claude_md", [])
    if not changed:
        return StepResult(name="ingest_claude_md", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="0 ingested (no changes)")

    ingest = _load_ingest_claude_md()
    # I3 fix: refresh BATCH_DATE per call (set at module import time otherwise).
    from datetime import datetime
    ingest.BATCH_DATE = datetime.now().strftime("%Y-%m-%d")

    argv = [
        "--dhg-root", str(ctx.config.dhg_root),
        "--projects", ",".join(_CLAUDE_MD_PROJECTS.keys()),
        "--registry-url", ctx.config.registry_url,
    ]
    try:
        ingest.main(argv=argv)
    except SystemExit:
        pass
    except Exception as e:
        logger.exception(f"ingest-claude-md failed: {e}")
        return StepResult(name="ingest_claude_md", success=False,
                          duration_seconds=time.monotonic() - start,
                          detail=str(e))

    ctx.results["claude_md_ingested"] = len(changed)
    return StepResult(name="ingest_claude_md", success=True,
                      duration_seconds=time.monotonic() - start,
                      detail=f"{len(changed)} CLAUDE.md files ingested")
```

Run: `pytest tests/test_steps.py -v -k test_step_ingest_claude_md`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add daemon/steps.py tests/test_steps.py scripts/ingest-claude-md.py
git commit -m "feat(daemon): add Step 4 (ingest CLAUDE.md), fix sys.path for container"
```

---

## Task 10: Step 5 — CodeGraph batch sync

**Files:**
- Modify: `daemon/steps.py`
- Modify: `tests/test_steps.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_steps.py`:

```python
def test_step_codegraph_sync_no_projects(ctx):
    from daemon.steps import step_codegraph_sync
    result = step_codegraph_sync(ctx)
    assert result.success


def test_step_codegraph_sync_skips_projects_without_codegraph(ctx, tmp_path):
    from daemon.steps import step_codegraph_sync
    project = tmp_path / "dhg" / "test-project"
    project.mkdir(parents=True)
    ctx.config.dhg_root = tmp_path / "dhg"
    result = step_codegraph_sync(ctx)
    assert result.success
    assert "0 projects synced" in result.detail
```

- [ ] **Step 2: Implement step 5**

Append to `daemon/steps.py`:

```python
import subprocess


def step_codegraph_sync(ctx: SweepContext) -> StepResult:
    """Step 5: Run `codegraph sync` for each DHG project containing .codegraph/.

    The existing PostToolUse hook for codegraph sync is kept — this step provides
    an additional batch sync that catches non-Claude edits (IDE saves, git ops).
    """
    start = time.monotonic()
    if not ctx.config.dhg_root.exists():
        return StepResult(name="codegraph_sync", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="no DHG_ROOT")

    synced = 0
    failed = 0
    for project_dir in ctx.config.dhg_root.iterdir():
        if not project_dir.is_dir():
            continue
        cg_dir = project_dir / ".codegraph"
        if not cg_dir.exists():
            continue
        try:
            subprocess.run(
                ["codegraph", "sync"],
                cwd=str(project_dir),
                timeout=20,
                capture_output=True,
                check=False,
            )
            synced += 1
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"codegraph sync failed in {project_dir}: {e}")
            failed += 1

    ctx.results["codegraph_synced"] = synced
    return StepResult(name="codegraph_sync", success=True,
                      duration_seconds=time.monotonic() - start,
                      detail=f"{synced} projects synced, {failed} failed")
```

Run: `pytest tests/test_steps.py -v -k test_step_codegraph_sync`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add daemon/steps.py tests/test_steps.py
git commit -m "feat(daemon): add Step 5 (codegraph batch sync)"
```

---

## Task 11: Step 6 — Materialize KB briefing + correction patterns JSON

**Files:**
- Modify: `daemon/steps.py`
- Modify: `tests/test_steps.py`

- [ ] **Step 1: Write failing test**

Append to `tests/test_steps.py`:

```python
def test_step_materialize_writes_files(ctx, tmp_path):
    from daemon.steps import step_materialize_views

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"ship_sessions": [], "deferred_items": [], "results": []}

    with patch("daemon.steps.httpx") as mock_httpx:
        mock_httpx.get.return_value = fake_resp
        mock_httpx.post.return_value = fake_resp
        mock_httpx.Timeout = MagicMock()
        result = step_materialize_views(ctx)

    assert result.success
    # At minimum one briefing file should be written per known project
    files = list(ctx.config.run_dir.glob("kb-briefing-*.json"))
    assert len(files) >= 1
```

- [ ] **Step 2: Implement step 6**

Append to `daemon/steps.py`:

```python
import httpx as _httpx
from datetime import datetime, timezone


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Materialization targets — same project list used in materialization, Serena, briefing
_PROJECTS_FOR_MATERIALIZATION = [
    "dhg-ai-factory", "portage", "c2l-vault", "claude-code-tresor", "digital-harmony-studio",
]


def _fetch_json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 5.0) -> dict | list | None:
    try:
        if method == "GET":
            resp = _httpx.get(url, timeout=timeout)
        else:
            resp = _httpx.post(url, json=payload or {}, timeout=timeout)
        if 200 <= resp.status_code < 300:
            return resp.json()
    except Exception as e:
        logger.debug(f"fetch {url} failed: {e}")
    return None


def step_materialize_views(ctx: SweepContext) -> StepResult:
    """Step 6: Pre-compute read-side payloads. Hooks read these instead of querying live.

    For each known project, writes:
      ~/.claude/run/kb-briefing-<project>.json
      ~/.claude/run/correction-patterns-<project>.json
    """
    start = time.monotonic()
    written = 0

    for project in _PROJECTS_FOR_MATERIALIZATION:
        base = ctx.config.registry_url

        ships = _fetch_json(f"{base}/api/ship-sessions?project_name={project}&limit=3") or {}
        # Oldest open high-priority items first (Task 0 added sort=created_at_asc).
        # This is the fix for the "lost deferred items" problem — recency-sorted queries
        # silently dropped old items behind the limit=5 window.
        deferred = _fetch_json(
            f"{base}/api/deferred-items?project_name={project}&status=open&priority=high"
            f"&sort=created_at_asc&limit=5"
        ) or {}
        # Bump last_surfaced_at on each item we're about to surface
        for item in (deferred.get("deferred_items", []) if isinstance(deferred, dict) else []):
            item_id = item.get("id")
            if item_id:
                try:
                    _httpx.post(f"{base}/api/deferred-items/{item_id}/surfaced", timeout=2.0)
                except Exception:
                    pass
        kb = _fetch_json(
            f"{base}/api/kb/search",
            method="POST",
            payload={
                "query": project,
                "project_name": project,
                "sources": ["decisions", "insights", "deferred_items", "ship_sessions"],
                "limit": 5,
            },
        ) or {}
        corr_stats = _fetch_json(f"{base}/api/corrections/stats") or {}

        briefing = {
            "project_name": project,
            "recent_ships": ships.get("ship_sessions", []) if isinstance(ships, dict) else [],
            "open_deferred_high": deferred.get("deferred_items", []) if isinstance(deferred, dict) else [],
            "relevant_prior_work": (kb.get("results", []) if isinstance(kb, dict) else kb) or [],
            "generated_at": _utcnow_iso(),
        }
        briefing_path = ctx.config.run_dir / f"kb-briefing-{project}.json"
        try:
            ctx.config.run_dir.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=ctx.config.run_dir, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(briefing, f, indent=2)
            os.replace(tmp, briefing_path)
            written += 1
        except OSError as e:
            logger.warning(f"failed to write {briefing_path}: {e}")

        patterns_payload = {
            "project_name": project,
            "patterns": corr_stats.get("categories", []) if isinstance(corr_stats, dict) else [],
            "generated_at": _utcnow_iso(),
        }
        patterns_path = ctx.config.run_dir / f"correction-patterns-{project}.json"
        try:
            fd, tmp = tempfile.mkstemp(dir=ctx.config.run_dir, suffix=".tmp")
            with os.fdopen(fd, "w") as f:
                json.dump(patterns_payload, f, indent=2)
            os.replace(tmp, patterns_path)
            written += 1
        except OSError:
            pass

    ctx.results["materialized_files"] = written
    ctx.results["materialization_at"] = time.time()
    return StepResult(name="materialize_views", success=True,
                      duration_seconds=time.monotonic() - start,
                      detail=f"wrote {written} files for {len(_PROJECTS_FOR_MATERIALIZATION)} projects")
```

Note: requires `import tempfile, os` at top of file — already present from prior tasks. Add `import httpx as _httpx` if not already imported.

Run: `pytest tests/test_steps.py -v -k test_step_materialize`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add daemon/steps.py tests/test_steps.py
git commit -m "feat(daemon): add Step 6 (materialize KB briefing + correction patterns)"
```

---

## Task 12: Step 7 — Serena digests

**Files:**
- Modify: `daemon/steps.py`
- Modify: `tests/test_steps.py`

- [ ] **Step 1: Write failing test**

```python
def test_step_serena_digest_writes_files(ctx, tmp_path):
    from daemon.steps import step_serena_digest
    project = tmp_path / "dhg" / "aifactory3.5" / "dhgaifactory3.5"
    project.mkdir(parents=True)
    (project / ".serena" / "memories").mkdir(parents=True)
    ctx.config.dhg_root = tmp_path / "dhg"

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {"results": [], "categories": []}

    with patch("daemon.steps._httpx") as mock_httpx:
        mock_httpx.get.return_value = fake_resp
        mock_httpx.post.return_value = fake_resp
        result = step_serena_digest(ctx)

    assert result.success
    daemon_dir = project / ".serena" / "memories" / "daemon"
    assert daemon_dir.exists()
```

- [ ] **Step 2: Implement step 7**

Append to `daemon/steps.py`:

```python
def step_serena_digest(ctx: SweepContext) -> StepResult:
    """Step 7: Write daemon-owned digest files to each project's .serena/memories/daemon/."""
    start = time.monotonic()
    base = ctx.config.registry_url
    written = 0

    for project, rel_path in _CLAUDE_MD_PROJECTS.items():
        proj_dir = ctx.config.dhg_root / rel_path
        serena_dir = proj_dir / ".serena" / "memories" / "daemon"
        if not (proj_dir / ".serena" / "memories").exists():
            continue
        serena_dir.mkdir(parents=True, exist_ok=True)

        kb = _fetch_json(
            f"{base}/api/kb/search",
            method="POST",
            payload={"query": project, "project_name": project,
                     "sources": ["decisions", "insights"], "limit": 10},
        ) or {}
        deferred = _fetch_json(
            f"{base}/api/deferred-items?project_name={project}&status=open&limit=20",
        ) or {}
        corr = _fetch_json(f"{base}/api/corrections/stats") or {}

        kb_results = (kb.get("results", []) if isinstance(kb, dict) else kb) or []
        deferred_items = (deferred.get("deferred_items", []) if isinstance(deferred, dict) else []) or []
        categories = corr.get("categories", []) if isinstance(corr, dict) else []

        kb_digest = "# KB Digest (auto-generated by memreg daemon)\n\n"
        kb_digest += f"Generated: {_utcnow_iso()}\n\n## Recent decisions and insights\n\n"
        for r in kb_results[:10]:
            title = (r.get("title") or r.get("tldr") or "")[:120]
            source = r.get("source", "?")
            kb_digest += f"- [{source}] {title}\n"
        _write_atomic(serena_dir / "kb_digest", kb_digest[:2000])

        open_items = "# Open Items (auto-generated by memreg daemon)\n\n"
        open_items += f"Generated: {_utcnow_iso()}\n\n"
        for d in deferred_items[:20]:
            title = (d.get("title") or "")[:120]
            priority = d.get("priority", "medium")
            open_items += f"- [{priority}] {title}\n"
        _write_atomic(serena_dir / "open_items", open_items[:2000])

        corr_md = "# Correction Patterns (auto-generated by memreg daemon)\n\n"
        corr_md += f"Generated: {_utcnow_iso()}\n\n"
        for c in sorted(categories, key=lambda x: -x.get("count_7d", 0))[:10]:
            cat = c.get("category", "?")
            count = c.get("count_7d", 0)
            if count > 0:
                corr_md += f"- {cat}: {count}x in 7d\n"
        _write_atomic(serena_dir / "correction_patterns", corr_md[:1000])

        written += 3

    ctx.results["serena_files_written"] = written
    return StepResult(name="serena_digest", success=True,
                      duration_seconds=time.monotonic() - start,
                      detail=f"wrote {written} digest files")


def _write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
```

Run: `pytest tests/test_steps.py -v -k test_step_serena_digest`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add daemon/steps.py tests/test_steps.py
git commit -m "feat(daemon): add Step 7 (Serena digest materialization)"
```

---

## Task 13: Step 8 — Rules-tier briefing (HARDENED)

**Why hardened:** This file auto-loads at project-instructions tier in every session. Bad content = noise injected forever. Mitigations:

1. **Kill switch** — `MEMREG_RULES_BRIEFING_DISABLED=1` skips Step 8 entirely.
2. **Quality gate** — only write the file if at least one correction pattern has `count_7d >= 2`. Quiet weeks = no file written = no noise.
3. **TTL** — if registry is unreachable for this sweep, delete the existing file (stale guidance is worse than no guidance).
4. **Filename `00-daemon-live-briefing.md`** — `00-` prefix ensures it loads FIRST among the project's rule files (alphabetical order). If you want it to matter, surface it first.
5. **Content discipline:**
   - Lead with active correction patterns (the attention payload).
   - Stale deferred items section uses oldest-first sort (Task 0) + only items with `last_surfaced_before_hours=24` so the daemon isn't re-shouting yesterday's items.
   - Drop "Key Recent Decisions" — most are historical and clutter the file.
6. **Observability** — `/briefing/<project>` HTTP endpoint (Task 14) returns the current briefing + last-write timestamp so you can read it without digging.

**Files:**
- Modify: `daemon/steps.py`
- Modify: `tests/test_steps.py`

- [ ] **Step 1: Write failing test**

```python
def test_step_rules_briefing_writes_00_prefixed_file(ctx, tmp_path):
    from daemon.steps import step_rules_briefing
    project = tmp_path / "dhg" / "aifactory3.5" / "dhgaifactory3.5"
    rules_dir = project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    ctx.config.dhg_root = tmp_path / "dhg"

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "categories": [{"category": "fabrication", "count_7d": 5}],
        "results": [],
        "deferred_items": [],
    }
    with patch("daemon.steps._httpx") as mock_httpx:
        mock_httpx.get.return_value = fake_resp
        mock_httpx.post.return_value = fake_resp
        result = step_rules_briefing(ctx)

    assert result.success
    briefing = rules_dir / "00-daemon-live-briefing.md"
    assert briefing.exists()
    content = briefing.read_text()
    assert "fabrication" in content
    assert "5x in 7" in content


def test_step_rules_briefing_quality_gate_no_file_when_quiet(ctx, tmp_path):
    """If no correction pattern has count_7d >= 2, no file should be written."""
    from daemon.steps import step_rules_briefing
    project = tmp_path / "dhg" / "aifactory3.5" / "dhgaifactory3.5"
    rules_dir = project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    ctx.config.dhg_root = tmp_path / "dhg"

    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "categories": [{"category": "fabrication", "count_7d": 1}],  # below threshold
        "results": [], "deferred_items": [],
    }
    with patch("daemon.steps._httpx") as mock_httpx:
        mock_httpx.get.return_value = fake_resp
        mock_httpx.post.return_value = fake_resp
        result = step_rules_briefing(ctx)

    assert result.success
    assert not (rules_dir / "00-daemon-live-briefing.md").exists()


def test_step_rules_briefing_kill_switch(ctx, tmp_path, monkeypatch):
    monkeypatch.setenv("MEMREG_RULES_BRIEFING_DISABLED", "1")
    from daemon.steps import step_rules_briefing
    project = tmp_path / "dhg" / "aifactory3.5" / "dhgaifactory3.5"
    rules_dir = project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    ctx.config.dhg_root = tmp_path / "dhg"

    result = step_rules_briefing(ctx)
    assert result.success
    assert "disabled" in result.detail.lower()
    assert not (rules_dir / "00-daemon-live-briefing.md").exists()


def test_step_rules_briefing_ttl_deletes_when_registry_down(ctx, tmp_path):
    """If registry returns nothing for all queries, existing briefing should be deleted."""
    from daemon.steps import step_rules_briefing
    project = tmp_path / "dhg" / "aifactory3.5" / "dhgaifactory3.5"
    rules_dir = project / ".claude" / "rules"
    rules_dir.mkdir(parents=True)
    stale = rules_dir / "00-daemon-live-briefing.md"
    stale.write_text("# stale content from prior sweep")
    ctx.config.dhg_root = tmp_path / "dhg"

    with patch("daemon.steps._httpx") as mock_httpx:
        mock_httpx.get.side_effect = Exception("registry down")
        mock_httpx.post.side_effect = Exception("registry down")
        result = step_rules_briefing(ctx)

    assert result.success
    assert not stale.exists()  # TTL: stale-delete when registry unreachable
```

- [ ] **Step 2: Implement step 8 (hardened)**

Append to `daemon/steps.py`:

```python
BRIEFING_FILENAME = "00-daemon-live-briefing.md"
CORRECTION_PATTERN_MIN_COUNT_7D = 2


def step_rules_briefing(ctx: SweepContext) -> StepResult:
    """Step 8: Write per-project 00-daemon-live-briefing.md at project-instructions tier.

    Project-scoped (not global ~/.claude/rules/) to prevent cross-project bleed.
    Filename `00-` prefix loads it FIRST among project rules.
    File is added to .gitignore by Task 21.

    Mitigations:
      - Kill switch: MEMREG_RULES_BRIEFING_DISABLED=1
      - Quality gate: only write if ≥1 correction pattern has count_7d ≥ 2
      - TTL: delete existing file if registry queries all fail (stale-delete)
    """
    start = time.monotonic()

    if os.environ.get("MEMREG_RULES_BRIEFING_DISABLED") == "1":
        return StepResult(name="rules_briefing", success=True,
                          duration_seconds=time.monotonic() - start,
                          detail="disabled via MEMREG_RULES_BRIEFING_DISABLED")

    base = ctx.config.registry_url
    written = 0
    deleted = 0

    for project, rel_path in _CLAUDE_MD_PROJECTS.items():
        rules_dir = ctx.config.dhg_root / rel_path / ".claude" / "rules"
        if not rules_dir.exists():
            continue
        briefing_path = rules_dir / BRIEFING_FILENAME

        # Fetch with explicit failure tracking
        corr = _fetch_json(f"{base}/api/corrections/stats")
        # Oldest-first deferred items not surfaced in last 24h (Task 0)
        deferred = _fetch_json(
            f"{base}/api/deferred-items?project_name={project}&status=open&priority=high"
            f"&sort=created_at_asc&last_surfaced_before_hours=24&limit=5"
        )

        # TTL: if all registry queries failed, delete existing file
        if corr is None and deferred is None:
            if briefing_path.exists():
                try:
                    briefing_path.unlink()
                    deleted += 1
                    logger.warning(f"Deleted stale briefing for {project}: registry unreachable")
                except OSError:
                    pass
            continue

        categories = (corr or {}).get("categories", []) if isinstance(corr, dict) else []
        active = [c for c in categories if c.get("count_7d", 0) >= CORRECTION_PATTERN_MIN_COUNT_7D]
        active.sort(key=lambda x: -x.get("count_7d", 0))

        deferred_items = (deferred or {}).get("deferred_items", []) if isinstance(deferred, dict) else []

        # Quality gate: skip writing entirely if no active patterns AND no stale items
        if not active and not deferred_items:
            if briefing_path.exists():
                try:
                    briefing_path.unlink()
                    deleted += 1
                except OSError:
                    pass
            continue

        # Bump last_surfaced_at on items we're about to surface
        for item in deferred_items:
            item_id = item.get("id")
            if item_id:
                try:
                    _httpx.post(f"{base}/api/deferred-items/{item_id}/surfaced", timeout=2.0)
                except Exception:
                    pass

        lines: list[str] = []
        lines.append("# Daemon Live Briefing (auto-generated)\n\n")
        lines.append(f"Generated: {_utcnow_iso()}  \n")
        lines.append(f"Source: dhg-memreg-agent daemon  \n")
        lines.append(f"Project: {project}\n\n")

        if active:
            lines.append("## Active Correction Patterns\n\n")
            for c in active[:5]:
                cat = c.get("category", "?")
                count = c.get("count_7d", 0)
                lines.append(f"- **{cat}** ({count}x in 7 days) — review before acting in this category\n")
            lines.append("\n")

        if deferred_items:
            lines.append("## Stale Open Items (oldest first, surfaced >24h ago)\n\n")
            lines.append("_These items have been open and haven't been surfaced recently — review whether they're blocking current work._\n\n")
            for d in deferred_items[:5]:
                t = (d.get("title") or "")[:140]
                created = d.get("created_at", "?")
                lines.append(f"- {t} _(open since {created[:10]})_\n")

        _write_atomic(briefing_path, "".join(lines))
        written += 1

    ctx.results["rules_briefings_written"] = written
    ctx.results["rules_briefings_deleted"] = deleted
    return StepResult(name="rules_briefing", success=True,
                      duration_seconds=time.monotonic() - start,
                      detail=f"wrote {written}, deleted {deleted}")
```

Run: `pytest tests/test_steps.py -v -k test_step_rules_briefing`
Expected: PASS (all 4 tests).

- [ ] **Step 3: Commit**

```bash
git add daemon/steps.py tests/test_steps.py
git commit -m "feat(daemon): Step 8 (rules-tier briefing) hardened — kill switch, quality gate, TTL, oldest-first"
```

---

## Task 14: Prometheus metrics + HTTP server (NO Step 9)

**Why no Step 9:** Earlier draft had a "step_update_metrics" sweep step that read the metrics object from `ctx.results["metrics"]` after the main loop injected it via `runner._metrics`. That was hack-on-hack. Simpler: `main()` already holds the metrics object — after `runner.run()` returns, the loop calls `metrics.record_*()` directly. The sweep ends with 8 steps, not 9.

**Files:**
- Create: `daemon/metrics.py`
- Create: `tests/test_metrics.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_metrics.py`:

```python
"""Tests for metrics module — Prometheus counters + /health + /metrics HTTP."""
import time
import urllib.request

import pytest

from daemon.metrics import MemregMetrics, MetricsServer


def test_record_sweep_increments_counters():
    metrics = MemregMetrics()
    metrics.record_sweep(duration_seconds=1.5, results=[])
    # Just verify call doesn't error
    assert metrics.last_sweep_at > 0


def test_record_capture_increments():
    metrics = MemregMetrics()
    metrics.record_capture(capture_type="insight", status="success")
    metrics.record_capture(capture_type="insight", status="failed")
    # No exception means recording works


def test_http_server_health_endpoint():
    metrics = MemregMetrics()
    metrics.record_sweep(1.0, [])
    server = MetricsServer(metrics, port=0)  # ephemeral port
    server.start()
    try:
        time.sleep(0.1)
        url = f"http://localhost:{server.port}/health"
        resp = urllib.request.urlopen(url, timeout=2)
        assert resp.status == 200
        body = resp.read().decode()
        assert "last_sweep_at" in body
    finally:
        server.stop()


def test_http_server_metrics_endpoint():
    metrics = MemregMetrics()
    metrics.record_capture("insight", "success")
    server = MetricsServer(metrics, port=0)
    server.start()
    try:
        time.sleep(0.1)
        url = f"http://localhost:{server.port}/metrics"
        resp = urllib.request.urlopen(url, timeout=2)
        body = resp.read().decode()
        assert "memreg_captures_total" in body
    finally:
        server.stop()
```

Run: `pytest tests/test_metrics.py -v`
Expected: FAIL.

- [ ] **Step 2: Implement metrics module (using prometheus_client.start_http_server)**

Create `daemon/metrics.py`:

```python
"""Prometheus metrics + minimal HTTP server.

Uses prometheus_client.start_http_server() for /metrics (it handles the threading,
socket reuse, and content negotiation correctly — no need to reimplement).

Adds a minimal stdlib /health and /briefing/<project> handler on a second port
for Docker healthcheck and observability.
"""
from __future__ import annotations

import http.server
import json
import logging
import os
import threading
import time
from pathlib import Path

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger("memreg.metrics")


class MemregMetrics:
    """Plain holder for prometheus_client metric objects + last_sweep_at."""

    def __init__(self):
        self.sweep_duration = Histogram(
            "memreg_sweep_duration_seconds", "Total duration of a sweep in seconds",
        )
        self.sweep_total = Counter("memreg_sweep_total", "Total sweeps completed")
        self.captures = Counter(
            "memreg_captures_total", "Capture POSTs", ["type", "status"],
        )
        self.dlq_depth = Gauge("memreg_dlq_depth", "Current DLQ depth")
        self.dlq_dropped = Counter("memreg_dlq_dropped_total", "DLQ entries dropped")
        self.ingestion = Counter(
            "memreg_ingestion_files_total", "Files ingested", ["source"],
        )
        self.active_sessions = Gauge(
            "memreg_active_sessions", "Sessions currently tracked by poller",
        )
        self.threshold_tokens = Gauge(
            "memreg_sweep_threshold_tokens", "Current sweep token threshold",
        )
        self.materialization_age = Gauge(
            "memreg_materialization_age_seconds",
            "Time since last successful materialization",
        )
        self.last_sweep_at: float = 0.0
        self._last_materialization_at: float = 0.0

    def record_sweep(self, duration_seconds: float) -> None:
        self.sweep_duration.observe(duration_seconds)
        self.sweep_total.inc()
        self.last_sweep_at = time.time()

    def record_capture(self, capture_type: str, status: str) -> None:
        self.captures.labels(type=capture_type, status=status).inc()

    def record_dlq(self, depth: int, dropped: int) -> None:
        self.dlq_depth.set(depth)
        if dropped > 0:
            self.dlq_dropped.inc(dropped)

    def record_ingestion(self, source: str, count: int) -> None:
        if count > 0:
            self.ingestion.labels(source=source).inc(count)

    def record_materialization_at(self, ts: float) -> None:
        self._last_materialization_at = ts
        self.materialization_age.set(max(0.0, time.time() - ts))


class _HealthHandler(http.server.BaseHTTPRequestHandler):
    metrics: MemregMetrics
    run_dir: Path

    def log_message(self, format, *args):
        pass  # silence access log

    def do_GET(self):
        if self.path == "/health":
            self._respond_json(200, {
                "status": "ok",
                "last_sweep_at": self.metrics.last_sweep_at,
            })
        elif self.path.startswith("/briefing/"):
            project = self.path[len("/briefing/"):]
            self._respond_briefing(project)
        else:
            self.send_response(404)
            self.end_headers()

    def _respond_json(self, code: int, body: dict):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def _respond_briefing(self, project: str):
        # Find the project's briefing file via DHG_ROOT env mapping
        dhg_root = Path(os.environ.get("DHG_ROOT", "/home/swebber64/DHG"))
        project_rels = {
            "dhg-ai-factory": "aifactory3.5/dhgaifactory3.5",
            "portage": "portage",
            "c2l-vault": "c2l-vault",
            "claude-code-tresor": "claude-code-tresor",
            "digital-harmony-studio": "Digital-Harmony-Studio-v1",
        }
        rel = project_rels.get(project)
        if rel is None:
            self._respond_json(404, {"error": f"unknown project: {project}"})
            return
        briefing = dhg_root / rel / ".claude" / "rules" / "00-daemon-live-briefing.md"
        if not briefing.exists():
            self._respond_json(404, {"error": "no briefing file (daemon may have quality-gated it)"})
            return
        try:
            content = briefing.read_text()
            mtime = briefing.stat().st_mtime
        except OSError as e:
            self._respond_json(500, {"error": str(e)})
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/markdown")
        self.send_header("X-Last-Modified", str(mtime))
        self.end_headers()
        self.wfile.write(content.encode())


class HealthServer:
    """Minimal HTTP server for /health and /briefing/<project>.

    /metrics is served separately by prometheus_client.start_http_server().
    """

    def __init__(self, metrics: MemregMetrics, port: int):
        self._metrics = metrics
        self._port = port
        self._server: http.server.HTTPServer | None = None

    @property
    def port(self) -> int:
        return self._server.server_address[1] if self._server else self._port

    def start(self) -> None:
        handler = type("Handler", (_HealthHandler,), {
            "metrics": self._metrics,
            "run_dir": Path(os.environ.get("MEMREG_RUN_DIR", "/home/swebber64/.claude/run")),
        })
        self._server = http.server.HTTPServer(("0.0.0.0", self._port), handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        logger.info(f"Health server listening on {self.port}")

    def stop(self) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


def start_metrics_server(port: int) -> None:
    """Start the prometheus /metrics endpoint."""
    start_http_server(port)
    logger.info(f"Prometheus metrics on port {port}")
```

Run: `pytest tests/test_metrics.py -v`
Expected: PASS. Adjust tests to call `start_metrics_server()` + `HealthServer` separately.

- [ ] **Step 3: No Step 9 to add — metrics update happens in `main()` after `runner.run()` returns**

The earlier draft had `step_update_metrics` reading metrics from `ctx.results["metrics"]`. Removed: the daemon main loop now does this directly. See Task 15 for the call site.

Run: `pytest tests/test_metrics.py tests/test_steps.py -v`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add daemon/metrics.py tests/test_metrics.py
git commit -m "feat(daemon): Prometheus metrics via start_http_server + minimal /health + /briefing endpoint"
```

---

## Task 15: Daemon main loop

**Files:**
- Create: `daemon/main.py`
- Create: `tests/test_main.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_main.py`:

```python
"""Smoke tests for daemon main loop."""
import os
from pathlib import Path

import pytest

from daemon.main import build_runner, load_config_from_env


def test_load_config_from_env_defaults(monkeypatch, tmp_path):
    monkeypatch.delenv("REGISTRY_URL", raising=False)
    monkeypatch.delenv("SWEEP_THRESHOLD_TOKENS", raising=False)
    cfg = load_config_from_env()
    assert cfg.registry_url == "http://10.0.0.251:8011"


def test_load_config_from_env_overrides(monkeypatch):
    monkeypatch.setenv("REGISTRY_URL", "http://test:9999")
    monkeypatch.setenv("SWEEP_TIMEOUT_SECONDS", "60")
    cfg = load_config_from_env()
    assert cfg.registry_url == "http://test:9999"
    assert cfg.sweep_timeout == 60


def test_build_runner_assembles_9_steps(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setenv("DHG_ROOT", str(tmp_path / "dhg"))
    cfg = load_config_from_env()
    cfg.run_dir = tmp_path / "run"
    from daemon.dlq import DeadLetterQueue
    dlq = DeadLetterQueue(dlq_file=cfg.run_dir / "dlq.jsonl")
    runner = build_runner(cfg, dlq)
    assert len(runner._steps) == 9
```

- [ ] **Step 2: Implement main loop**

Create `daemon/main.py`:

```python
"""dhg-memreg-agent daemon main loop.

Entry point for the dhg-memreg Docker container.

Flow:
  1. Load config from env vars
  2. Start metrics HTTP server (port 8018)
  3. Construct poller + DLQ + sweep runner
  4. Loop forever: poll → if hits, run sweep → sleep SWEEP_INTERVAL_SECONDS
"""
from __future__ import annotations

import logging
import os
import signal
import sys
import time
from pathlib import Path

from daemon.dlq import DeadLetterQueue
from daemon.metrics import MemregMetrics, HealthServer, start_metrics_server
from daemon.poller import TranscriptPoller
from daemon.sweep import SweepConfig, SweepRunner, StepDef
from daemon.steps import (
    step_capture_guarantee,
    step_dlq_retry,
    step_ingest_memory,
    step_ingest_claude_md,
    step_codegraph_sync,
    step_materialize_views,
    step_serena_digest,
    step_rules_briefing,
)

logger = logging.getLogger("memreg.daemon")


def load_config_from_env() -> SweepConfig:
    return SweepConfig(
        registry_url=os.environ.get("REGISTRY_URL", "http://10.0.0.251:8011"),
        projects_dir=Path(os.environ.get("CLAUDE_PROJECTS_DIR", str(Path.home() / ".claude/projects"))),
        dhg_root=Path(os.environ.get("DHG_ROOT", str(Path.home() / "DHG"))),
        run_dir=Path(os.environ.get("MEMREG_RUN_DIR", str(Path.home() / ".claude/run"))),
        sweep_timeout=int(os.environ.get("SWEEP_TIMEOUT_SECONDS", "180")),
    )


def build_runner(config: SweepConfig, dlq: DeadLetterQueue) -> SweepRunner:
    # 8 steps. Metrics update happens in main() after runner.run_with_ctx() returns.
    steps = [
        StepDef(name="capture_guarantee", fn=step_capture_guarantee, timeout=30),
        StepDef(name="dlq_retry", fn=step_dlq_retry, timeout=30),
        StepDef(name="ingest_memory", fn=step_ingest_memory, timeout=60),
        StepDef(name="ingest_claude_md", fn=step_ingest_claude_md, timeout=60),
        StepDef(name="codegraph_sync", fn=step_codegraph_sync, timeout=30),
        StepDef(name="materialize_views", fn=step_materialize_views, timeout=30),
        StepDef(name="serena_digest", fn=step_serena_digest, timeout=15),
        StepDef(name="rules_briefing", fn=step_rules_briefing, timeout=10),
    ]
    return SweepRunner(config=config, dlq=dlq, steps=steps)


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )
    logger.info("dhg-memreg-agent daemon starting")

    config = load_config_from_env()
    threshold = int(os.environ.get("SWEEP_THRESHOLD_TOKENS", "100000"))
    interval = int(os.environ.get("SWEEP_INTERVAL_SECONDS", "30"))
    metrics_port = int(os.environ.get("METRICS_PORT", "8018"))
    dlq_max_age = int(os.environ.get("DLQ_MAX_AGE_DAYS", "7"))
    dlq_max_entries = int(os.environ.get("DLQ_MAX_ENTRIES", "1000"))

    config.run_dir.mkdir(parents=True, exist_ok=True)

    metrics = MemregMetrics()
    metrics.threshold_tokens.set(threshold)
    start_metrics_server(metrics_port)
    health_server = HealthServer(metrics, port=metrics_port + 1)  # /health + /briefing
    health_server.start()

    dlq = DeadLetterQueue(
        dlq_file=config.run_dir / "memreg-dlq.jsonl",
        registry_url=config.registry_url,
        max_age_days=dlq_max_age,
        max_entries=dlq_max_entries,
    )
    poller = TranscriptPoller(
        projects_dir=config.projects_dir,
        state_file=config.run_dir / "memreg-sweep-state.json",
        threshold_tokens=threshold,
    )
    runner = build_runner(config, dlq)

    stop_flag = {"value": False}

    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        stop_flag["value"] = True

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info(
        f"Daemon ready — threshold={threshold} tokens, interval={interval}s, "
        f"registry={config.registry_url}, metrics_port={metrics_port}"
    )

    try:
        while not stop_flag["value"]:
            try:
                hits = poller.check()
                if hits:
                    logger.info(f"Threshold crossed for {len(hits)} sessions, firing sweep")
                    sweep_start = time.monotonic()
                    # SweepRunner.run() returns (step_results, final_ctx) — see Task 3 patch
                    step_results, final_ctx = runner.run_with_ctx(hits)
                    duration = time.monotonic() - sweep_start

                    # Update metrics directly — no Step 9 indirection
                    metrics.record_sweep(duration_seconds=duration)
                    metrics.record_dlq(
                        depth=dlq.depth(),
                        dropped=final_ctx.results.get("dlq_dropped", 0),
                    )
                    metrics.record_ingestion("memory", final_ctx.results.get("memory_files_ingested", 0))
                    metrics.record_ingestion("claude_md", final_ctx.results.get("claude_md_ingested", 0))
                    if "materialization_at" in final_ctx.results:
                        metrics.record_materialization_at(final_ctx.results["materialization_at"])
                    metrics.active_sessions.set(len(hits))
            except Exception:
                logger.exception("Loop iteration error")
            # Sleep in small increments so SIGTERM is responsive
            for _ in range(interval):
                if stop_flag["value"]:
                    break
                time.sleep(1)
    finally:
        health_server.stop()
        logger.info("Daemon stopped")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Run: `pytest tests/test_main.py -v`
Expected: PASS.

- [ ] **Step 3: Wire metrics injection into runner**

The `step_update_metrics` step reads `ctx.results["metrics"]`. The main loop must inject it before calling `runner.run()`. Update `daemon/main.py` `main()` loop:

Replace:
```python
results = runner.run(hits)
```

With:
```python
runner._steps  # access steps list — but we need a cleaner way
# Use a closure: re-bind step_update_metrics to capture the metrics object
```

Cleaner approach — modify `step_update_metrics` to accept metrics from a module-level set/get, or wrap the steps in a closure at runner construction. Simplest: inject via SweepContext.results before sweep runs. Add to `SweepRunner.run()` an optional `initial_results` dict OR pass it via `build_runner`. Update `build_runner` signature to accept metrics:

Edit `daemon/main.py` `build_runner`:
```python
def build_runner(config: SweepConfig, dlq: DeadLetterQueue, metrics: "MemregMetrics" = None) -> SweepRunner:
    runner = SweepRunner(config=config, dlq=dlq, steps=[...])
    runner._metrics = metrics  # attach for sweep injection
    return runner
```

And edit `daemon/sweep.py` `SweepRunner.run()`:
```python
ctx = SweepContext(config=self._config, dlq=self._dlq, sessions=sessions, results={})
if getattr(self, "_metrics", None) is not None:
    ctx.results["metrics"] = self._metrics
```

Update `daemon/main.py` to pass metrics:
```python
runner = build_runner(config, dlq, metrics=metrics)
```

Run: `pytest tests/ -v`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add daemon/main.py daemon/sweep.py tests/test_main.py
git commit -m "feat(daemon): add main loop with signal handling and metrics injection"
```

---

## Task 16: Dockerfile + smoke tests

**Files:**
- Modify: `Dockerfile`
- Modify: `docker/entrypoint.sh` (add `daemon` command)

- [ ] **Step 1: Update Dockerfile**

Replace `~/DHG/dhg-memreg/Dockerfile` contents:

```dockerfile
# dhg-memreg — DHG memory + registry capture toolchain + autonomous daemon
#
# Single image, multiple entry modes:
#   1. Daemon (default):  docker run dhg-memreg daemon
#   2. Capture/ingest:    docker run dhg-memreg <command> <args...>
#
# Commands (same as before):
#   post-bug-fixes, post-correction, post-decision-logs, post-deferred-items,
#   post-insight, post-ship-session, post-test-coverage
#   ingest-memory-files, ingest-claude-md
#
# New command:
#   daemon  →  run the autonomous polling daemon (main process for container deploy)
#
# LAN-only: assumes registry reachable at REGISTRY_URL (default http://10.0.0.251:8011).

FROM python:3.12-slim AS runtime

WORKDIR /memreg

# Install curl for bash capture scripts + codegraph CLI dependency
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Python deps (httpx, tiktoken, prometheus_client)
COPY docker/requirements.txt /memreg/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Smoke test — fail build if tiktoken wheel didn't install (advisor C2)
RUN python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" \
  && python -c "import prometheus_client" \
  && python -c "import httpx"

# Scripts (capture + ingest)
COPY scripts/ /memreg/scripts/
RUN chmod +x /memreg/scripts/*.sh

# Daemon package
COPY daemon/ /memreg/daemon/

# Hooks needed by daemon (capture-guarantee.py)
COPY hooks/ /memreg/hooks/

# Entrypoint dispatcher
COPY docker/entrypoint.sh /memreg/entrypoint.sh
RUN chmod +x /memreg/entrypoint.sh

ENV REGISTRY_URL=http://10.0.0.251:8011 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/memreg

# Run as UID 1000 to match host swebber64 — files written to volume mounts
# will be owned by the host user (advisor finding G3).
RUN useradd -u 1000 -ms /bin/bash memreg \
  && mkdir -p /home/memreg/.claude /home/memreg/DHG \
  && chown -R memreg:memreg /memreg /home/memreg
USER memreg

ENTRYPOINT ["/memreg/entrypoint.sh"]
CMD ["daemon"]
```

- [ ] **Step 2: Update entrypoint.sh to handle daemon command**

Edit `docker/entrypoint.sh`. Add to the help text:

```
Daemon command:
  daemon                → run autonomous polling daemon (main container entry)
```

Add daemon dispatch above the existing bash/py script dispatch:

```bash
# Daemon mode — main container entrypoint
if [ "$cmd" = "daemon" ]; then
  exec python3 -m daemon.main
fi
```

- [ ] **Step 3: Build the image**

```bash
cd ~/DHG/dhg-memreg
docker build -t dhg-memreg:daemon-test .
```
Expected: BUILD succeeds, smoke tests pass.

- [ ] **Step 4: Run smoke test**

```bash
docker run --rm dhg-memreg:daemon-test --help
docker run --rm dhg-memreg:daemon-test post-insight '{"tldr":"build-test","insight_statement":"build smoke test","project_name":"dhg-ai-factory","category":"infra","tags":["smoke"],"model_name":"build"}'
```
Expected: help displays daemon command; capture command still works.

- [ ] **Step 5: Commit**

```bash
git add Dockerfile docker/entrypoint.sh
git commit -m "feat(docker): add daemon entrypoint, tiktoken smoke test, UID 1000 user"
```

---

## Task 17: docker-compose.override.yml entry

**Files:**
- Modify: `~/DHG/aifactory3.5/dhgaifactory3.5/docker-compose.override.yml`

**Risk:** HIGH — touches running infrastructure. Stephen must approve container deploy.

- [ ] **Step 1: Confirm ports 8018 and 8019 are free**

```bash
sudo lsof -iTCP:8018 -sTCP:LISTEN
sudo lsof -iTCP:8019 -sTCP:LISTEN
docker ps --format '{{.Names}} {{.Ports}}' | grep -E "8018|8019"
```
Expected: no output (both ports free). 8018 = /metrics (prometheus_client). 8019 = /health + /briefing.

- [ ] **Step 2: Add service to override**

Add to `docker-compose.override.yml` under `services:`:

```yaml
  dhg-memreg-agent:
    build: /home/swebber64/DHG/dhg-memreg
    image: dhg-memreg:daemon
    container_name: dhg-memreg-agent
    network_mode: host
    user: "1000:1000"
    volumes:
      - /home/swebber64/.claude:/home/swebber64/.claude
      - /home/swebber64/DHG:/home/swebber64/DHG
    restart: unless-stopped
    environment:
      - REGISTRY_URL=http://10.0.0.251:8011
      - SWEEP_THRESHOLD_TOKENS=100000
      - SWEEP_INTERVAL_SECONDS=30
      - SWEEP_TIMEOUT_SECONDS=180
      - DLQ_MAX_AGE_DAYS=7
      - DLQ_MAX_ENTRIES=1000
      - CLAUDE_PROJECTS_DIR=/home/swebber64/.claude/projects
      - DHG_ROOT=/home/swebber64/DHG
      - MEMREG_RUN_DIR=/home/swebber64/.claude/run
      - METRICS_PORT=8018
      - REGISTRY_SRC_PATH=/home/swebber64/DHG/aifactory3.5/dhgaifactory3.5/registry
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8019/health || exit 1"]
      interval: 60s
      timeout: 5s
      retries: 3
      start_period: 30s
```

- [ ] **Step 3: Bring up the service**

```bash
cd ~/DHG/aifactory3.5/dhgaifactory3.5
docker compose up -d --build dhg-memreg-agent
docker compose logs -f --tail 50 dhg-memreg-agent
```
Expected: container starts, logs show "Daemon ready — threshold=100000 tokens..."

- [ ] **Step 4: Verify health + metrics endpoints**

```bash
curl -s http://10.0.0.251:8019/health
curl -s http://10.0.0.251:8019/briefing/dhg-ai-factory | head -20
curl -s http://10.0.0.251:8018/metrics | head -30
docker compose ps dhg-memreg-agent
```
Expected: `/health` returns 200 JSON; `/metrics` shows memreg_* counters; container status healthy.

- [ ] **Step 5: Commit**

```bash
cd ~/DHG/aifactory3.5/dhgaifactory3.5
git add docker-compose.override.yml
git commit -m "feat(infra): deploy dhg-memreg-agent daemon on port 8018"
```

**Rollback:** `docker compose stop dhg-memreg-agent && docker compose rm -f dhg-memreg-agent && git revert HEAD`

---

## Task 18: Modify SessionStart KB-briefing hook

**Files:**
- Modify: `~/DHG/dhg-memreg/hooks/session-start-kb-briefing.sh`

- [ ] **Step 1: Replace live curls with file read**

Edit `hooks/session-start-kb-briefing.sh`. Replace the 4-parallel-curl section (lines ~72-127) with:

```bash
# --- Read pre-computed briefing from materialized file (daemon Step 6) ---
BRIEFING_FILE="${HOME}/.claude/run/kb-briefing-${PROJECT_NAME}.json"

if [ -f "$BRIEFING_FILE" ]; then
  # Daemon-materialized — use it
  ship_titles=$(jq -r '.recent_ships[]? | "  - \(.feature // "(untitled)") [\(.status // "?")]"' "$BRIEFING_FILE" 2>/dev/null)
  [ -z "$ship_titles" ] && ship_titles="  (no ship sessions yet)"

  deferred_titles=$(jq -r '.open_deferred_high[]? | "  - \(.title // "(untitled)") [\(.reason // "no-reason")]" | .[0:140]' "$BRIEFING_FILE" 2>/dev/null)
  [ -z "$deferred_titles" ] && deferred_titles="  (no high-priority deferred items)"

  kb_titles=$(jq -r '.relevant_prior_work[]? | "  - [\(.source // "?")] \(.title // .tldr // "(untitled)")" | .[0:140]' "$BRIEFING_FILE" 2>/dev/null)
  [ -z "$kb_titles" ] && kb_titles="  (no KB matches)"

  generated_at=$(jq -r '.generated_at // "unknown"' "$BRIEFING_FILE" 2>/dev/null)
  staleness_marker="(daemon-cached: ${generated_at})"
else
  # No briefing file yet — daemon hasn't run, fall back to silent skip
  ship_titles="  (briefing pending — daemon hasn't run yet)"
  deferred_titles="  (briefing pending)"
  kb_titles="  (briefing pending)"
  staleness_marker="(no daemon briefing)"
fi
```

The output block stays as-is, just gains a staleness marker line.

- [ ] **Step 2: Test the hook manually**

```bash
PROJECT_NAME=dhg-ai-factory bash ~/DHG/dhg-memreg/hooks/session-start-kb-briefing.sh
```
Expected: prints briefing using materialized data or "briefing pending" fallback.

- [ ] **Step 3: Commit**

```bash
cd ~/DHG/dhg-memreg
git add hooks/session-start-kb-briefing.sh
git commit -m "refactor(hooks): SessionStart reads daemon-materialized briefing instead of live curls"
```

---

## Task 19: Modify UserPromptSubmit hook

**Files:**
- Modify: `~/DHG/dhg-memreg/hooks/user-prompt-kb-inject.sh`

- [ ] **Step 1: Replace live curls with file read**

Edit `hooks/user-prompt-kb-inject.sh`. Replace the 2 parallel curls (lines ~60-77) with:

```bash
PATTERNS_FILE="${HOME}/.claude/run/correction-patterns-${PROJECT}.json"
BRIEFING_FILE="${HOME}/.claude/run/kb-briefing-${PROJECT}.json"

# Active correction pattern
top_cat=""
top_count=0
if [ -f "$PATTERNS_FILE" ]; then
  top_cat=$(jq -r '[.patterns[]? | select(.count_7d > 0)] | sort_by(-.count_7d) | .[0].category // empty' "$PATTERNS_FILE" 2>/dev/null)
  top_count=$(jq -r '[.patterns[]? | select(.count_7d > 0)] | sort_by(-.count_7d) | .[0].count_7d // 0' "$PATTERNS_FILE" 2>/dev/null)
fi

# KB results (filtered to the user's prompt keywords would be ideal, but the daemon
# materializes a project-scoped list — use that as-is, daemon refreshes every sweep)
kb_count=0
kb_results=""
if [ -f "$BRIEFING_FILE" ]; then
  kb_count=$(jq -r '.relevant_prior_work | length' "$BRIEFING_FILE" 2>/dev/null || echo "0")
  if [ "$kb_count" != "0" ] && [ "$kb_count" != "null" ]; then
    kb_results=$(jq -r '.relevant_prior_work[] | "- [\(.source // "?")] \(.title // .tldr // "(untitled)" | .[0:120])"' "$BRIEFING_FILE" 2>/dev/null)
  fi
fi
```

Remove the curl/wait blocks. The injection logic at the end stays the same.

- [ ] **Step 2: Test**

```bash
echo '{"prompt":"how does the auth middleware work"}' | bash ~/DHG/dhg-memreg/hooks/user-prompt-kb-inject.sh
```
Expected: emits JSON with `additionalContext` from the materialized file, or exits silently if no file.

- [ ] **Step 3: Commit**

```bash
git add hooks/user-prompt-kb-inject.sh
git commit -m "refactor(hooks): UserPromptSubmit reads daemon-materialized patterns instead of live curls"
```

---

## Task 20: Remove capture-guarantee Stop hook

**Files:**
- Modify: `~/.claude/settings.json`

**Risk:** medium — affects all Claude Code sessions on this machine.

- [ ] **Step 1: Backup current settings**

```bash
cp ~/.claude/settings.json ~/.claude/settings.json.bak-pre-daemon
```

- [ ] **Step 2: Show current Stop hooks**

```bash
jq '.hooks.Stop' ~/.claude/settings.json
```
Expected: shows array with memory-sync, session-capture, and capture-guarantee entries.

- [ ] **Step 3: Remove capture-guarantee from Stop hooks**

Use `jq` to filter out the capture-guarantee entry:

```bash
jq '.hooks.Stop |= map(select(.hooks | all(.command | contains("capture-guarantee.py") | not)))' \
  ~/.claude/settings.json > /tmp/settings.json.new \
  && jq . /tmp/settings.json.new >/dev/null \
  && mv /tmp/settings.json.new ~/.claude/settings.json
```

- [ ] **Step 4: Verify**

```bash
jq '.hooks.Stop' ~/.claude/settings.json
```
Expected: array no longer contains the capture-guarantee.py entry. Other Stop hooks (memory-sync, session-capture) remain.

**Rollback:** `cp ~/.claude/settings.json.bak-pre-daemon ~/.claude/settings.json`

---

## Task 21: Gitignore 00-daemon-live-briefing.md

**Files:**
- Modify: `~/DHG/aifactory3.5/dhgaifactory3.5/.gitignore`
- Modify: `~/DHG/portage/.gitignore` (if exists)
- Modify: `~/DHG/Digital-Harmony-Studio-v1/.gitignore` (if exists)

- [ ] **Step 1: Add to each project's .gitignore**

For each DHG project that exists, append to `.gitignore`:

```
# daemon-materialized briefing (auto-regenerated by dhg-memreg-agent)
.claude/rules/00-daemon-live-briefing.md
```

- [ ] **Step 2: Commit per-project**

```bash
cd ~/DHG/aifactory3.5/dhgaifactory3.5
git add .gitignore
git commit -m "chore: ignore daemon-live-briefing.md (auto-generated)"
```

Repeat for portage and any other project.

---

## Task 22: End-to-end integration verification

**Files:** (no edits — verification only)

- [ ] **Step 1: Confirm daemon is running**

```bash
docker compose ps dhg-memreg-agent
curl -s http://10.0.0.251:8018/health | jq .
```
Expected: container `running (healthy)`, /health returns JSON.

- [ ] **Step 2: Trigger a sweep manually by injecting tokens**

The cleanest manual trigger: append a large JSONL block to an existing session transcript.

```bash
# Find a current session transcript
ls -lat ~/.claude/projects/-home-swebber64-DHG-aifactory3-5-dhgaifactory3-5/*.jsonl | head -3

# Wait for the daemon to baseline (it does so on first poll, ~30s after start)
# Then check that materialization files are written within 30-60s of next sweep:
sleep 60
ls -la ~/.claude/run/kb-briefing-*.json
ls -la ~/.claude/run/correction-patterns-*.json
ls -la ~/DHG/aifactory3.5/dhgaifactory3.5/.claude/rules/00-daemon-live-briefing.md
```
Expected: files exist with recent mtimes; JSON files are valid.

- [ ] **Step 3: Inject a DLQ entry and verify retry**

```bash
echo '{"endpoint":"post-insight","payload":"{\"tldr\":\"dlq-test\",\"insight_statement\":\"daemon dlq retry test\",\"project_name\":\"dhg-ai-factory\",\"category\":\"infra\",\"tags\":[\"daemon-test\"],\"model_name\":\"test\"}","timestamp":'$(date +%s)',"attempts":1}' >> ~/.claude/run/memreg-dlq.jsonl

# Wait for next sweep (up to 30s + sweep duration)
sleep 60

# Check that DLQ depth dropped (entry was retried successfully)
wc -l ~/.claude/run/memreg-dlq.jsonl
```
Expected: DLQ depth decreases.

- [ ] **Step 4: Verify hooks read materialized files**

```bash
PROJECT_NAME=dhg-ai-factory bash ~/DHG/dhg-memreg/hooks/session-start-kb-briefing.sh | head -20
echo '{"prompt":"check the daemon materialization is working"}' | bash ~/DHG/dhg-memreg/hooks/user-prompt-kb-inject.sh
```
Expected: hooks emit content from materialized files (not live queries).

- [ ] **Step 5: Verify Prometheus metrics**

```bash
curl -s http://10.0.0.251:8018/metrics | grep memreg_
```
Expected: counters and gauges visible. At least `memreg_sweep_total`, `memreg_dlq_depth`, `memreg_active_sessions`.

- [ ] **Step 6: Check that Stop hook no longer fires capture-guarantee**

Start a new Claude Code session, type something trivial, exit. Then check `~/.claude/run/capture-guarantee.log`:

```bash
tail -5 ~/.claude/run/capture-guarantee.log
```
Expected: no new entries from the test session (Stop hook removed). Daemon-driven sweep handles capture instead.

- [ ] **Step 7: Capture the ship session**

The /ship workflow's Phase 7 will fire this automatically. Manual fallback:

```bash
~/.claude/scripts/post-ship-session.sh "$(cat <<'EOF'
{
  "project_name": "dhg-ai-factory",
  "feature": "dhg-memreg-agent daemon",
  "approach": "Python polling daemon, token-based threshold (tiktoken cl100k_base, 100K tokens), 9-step sweep with threading timeouts, DLQ for failed captures, mtime-driven ingestion, materialized read-side views, project-scoped rules-tier briefing, Prometheus metrics.",
  "status": "complete",
  "complexity": "complex",
  "tdd": true,
  "branch": "master",
  "tags": ["memreg","daemon","autonomous-pipeline","observability"]
}
EOF
)"
```

---

## Success criteria

1. **Daemon container running on g700data1** — `docker compose ps dhg-memreg-agent` shows healthy.
2. **Token-based sweep triggers** — appending ~100K tokens of activity to a session transcript fires a sweep within 30s.
3. **DLQ retry works** — entries injected into the DLQ are retried and removed on successful POST.
4. **Materialized files exist** — `~/.claude/run/kb-briefing-*.json` and `correction-patterns-*.json` are present and refreshed each sweep.
5. **Hooks read from files** — SessionStart and UserPromptSubmit hooks deliver briefing from local files (no live registry queries) and complete in <100ms.
6. **Rules-tier briefing exists** — `.claude/rules/00-daemon-live-briefing.md` is written per project and is gitignored.
7. **Prometheus metrics exposed** — `curl http://10.0.0.251:8018/metrics` shows memreg_* counters.
8. **Stop hook removed** — capture-guarantee.py is no longer fired by Claude Code's Stop event.
9. **No regression** — all existing 52 tests still pass plus new daemon tests.
