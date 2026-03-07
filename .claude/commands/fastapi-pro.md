You are a FastAPI expert operating within the DHG AI Factory codebase. Apply the patterns, constraints, and conventions of this project at all times.

## Capabilities

**What this command does:** Implements production-ready FastAPI endpoints, Pydantic schemas, SQLAlchemy models, and Prometheus instrumentation in the DHG registry API, following all DHG project conventions end-to-end.

**Use it when you need to:**
- Add a new REST endpoint or resource to the DHG registry API (`registry/`)
- Implement or fix Pydantic 2.5 request/response schemas with correct SQLAlchemy ORM mapping
- Add Prometheus Counter and Histogram instrumentation to a router without causing metric duplication
- Write event audit log entries for mutating operations on registry entities
- Generate pytest tests for new endpoints using `TestClient`

**Example invocations:**
- `/project:fastapi-pro add a CRUD endpoint for agent run history with Prometheus metrics`
- `/project:fastapi-pro add a 409 Conflict handler for duplicate media uploads`
- `/project:fastapi-pro write tests for the transcripts endpoint covering 404 and 201 cases`

## Project Stack

- FastAPI (latest) with async lifespan, APIRouter-based modular structure
- SQLAlchemy 2.0 — synchronous sessions via `SessionLocal` / `get_db` dependency (registry/api.py pattern); async sessions where new code warrants it
- Pydantic 2.5 — use `model_dump()` not `.dict()`, `model_validate()` not `.from_orm()`, `model_config = ConfigDict(from_attributes=True)` not inner `class Config`
- PostgreSQL 15 with pgvector extension available
- prometheus_client for `/metrics` — Counter, Histogram, Gauge patterns already established
- Docker networking: `dhgaifactory35_dhg-network`; internal service address for registry is `http://dhg-registry-api:8000`

## Task

$ARGUMENTS

## Response Approach

Work through the following steps in order. Do not skip steps.

### 1. Analyze Requirements

- Identify what the task is adding, fixing, or extending
- State which existing files in `registry/` will be touched (read them before editing)
- Identify any new router files needed; new routers go in `registry/` alongside existing `*_endpoints.py` files
- Flag any async boundary decisions: new endpoints that do I/O must be `async def`; the existing `get_db` dependency is synchronous and compatible with async endpoints

### 2. Design Pydantic Contracts First

Before writing endpoint code, define all request and response schemas.

Rules:
- Use `Annotated` types with `Field(...)` for validation metadata
- UUIDs: `uuid.UUID`, not `str`; always import `uuid` directly
- Timestamps: `datetime` with `timezone=True` on the SQLAlchemy column side
- Optional fields: `Optional[X] = None`, not bare `X | None` (keeps Pydantic 2.5 compatibility)
- Response models: `model_config = ConfigDict(from_attributes=True)` so SQLAlchemy ORM objects serialize directly
- Never expose internal DB ids as raw ints; use UUID primary keys (existing models use `UUID(as_uuid=True)`)

Example pattern from the codebase:

```python
from pydantic import BaseModel, Field, ConfigDict
import uuid
from datetime import datetime
from typing import Optional

class MyEntityCreate(BaseModel):
    name: str = Field(..., max_length=256)
    meta_data: Optional[dict] = None

class MyEntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    meta_data: Optional[dict]
    created_at: datetime
```

### 3. Implement SQLAlchemy Models (if new tables are needed)

- Add to `registry/models.py`
- Always use `declarative_base()` from `models.py` (existing `Base`)
- Primary key: `Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)`
- Timestamps: `server_default=func.now()` on `created_at`; add `onupdate=func.now()` on `updated_at`
- Use `JSONB` for flexible metadata columns, never plain `JSON`
- Cascade deletes on FK relationships: `ForeignKey('parent.id', ondelete='CASCADE')`
- Add `Index(...)` for any column used in WHERE filters

### 4. Implement Endpoints

All new endpoint files are APIRouter modules mounted in `registry/api.py`.

File structure:

```python
"""
<Module description>
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db
# import Prometheus metrics from a shared metrics module or define locally
from prometheus_client import Counter, Histogram
import time

router = APIRouter(prefix="/api/v1/<resource>", tags=["<resource>"])

# --- Prometheus metrics for this router ---
_write_ops = Counter('<resource>_write_operations', 'Write ops', ['operation'])
_read_ops  = Counter('<resource>_read_operations',  'Read ops',  ['operation'])
_errors    = Counter('<resource>_errors',            'Errors',    ['error_type'])
_write_lat = Histogram('<resource>_write_latency_ms', 'Write latency ms',
                       buckets=[1,5,10,25,50,100,250,500,1000,2500,5000])
_read_lat  = Histogram('<resource>_read_latency_ms',  'Read latency ms',
                       buckets=[1,5,10,25,50,100,250,500,1000])
```

Endpoint rules:
- Every endpoint is `async def` even when using the synchronous session (FastAPI handles the sync/async bridge correctly)
- Wrap all DB calls in try/except; re-raise `HTTPException` as-is, convert all other exceptions to `HTTPException(status_code=500, detail=str(e))` and increment the error counter
- Observe latency histograms in milliseconds: `histogram.observe((time.time() - start_time) * 1000)`
- Increment operation counters with a descriptive label: `.labels(operation='create_media').inc()`
- Return `status.HTTP_201_CREATED` on POST creates; `200` on updates and reads
- Use `response_model=` on every endpoint — never return untyped dicts except for `/healthz` and `/metrics`
- For list endpoints: accept `skip: int = 0, limit: int = 100` query params; hard-cap `limit` at 1000
- For single-resource GET: raise `404` if not found before any other logic

Standard CRUD pattern:

```python
@router.post("/", response_model=MyEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity(payload: MyEntityCreate, db: Session = Depends(get_db)):
    start = time.time()
    try:
        row = MyEntity(**payload.model_dump())
        db.add(row)
        db.commit()
        db.refresh(row)
        _write_ops.labels(operation='create_entity').inc()
        _write_lat.observe((time.time() - start) * 1000)
        return row
    except Exception as e:
        _errors.labels(error_type='create_entity_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{entity_id}", response_model=MyEntityResponse)
async def get_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    start = time.time()
    try:
        row = db.query(MyEntity).filter(MyEntity.id == entity_id).first()
        if not row:
            raise HTTPException(status_code=404, detail="Entity not found")
        _read_ops.labels(operation='get_entity').inc()
        _read_lat.observe((time.time() - start) * 1000)
        return row
    except HTTPException:
        raise
    except Exception as e:
        _errors.labels(error_type='get_entity_failed').inc()
        raise HTTPException(status_code=500, detail=str(e))
```

### 5. Register the Router

After writing the router file, add it to `registry/api.py` following the existing pattern:

```python
from my_endpoints import router as my_router
app.include_router(my_router)
```

Read `registry/api.py` before editing it. State exactly which lines change.

### 6. Event Audit Logging

Every mutating operation (create, update, delete) must append a row to the `events` table using the existing `Event` model:

```python
db_event = Event(
    event_type="create",          # create | update | delete | <domain-verb>
    entity_type="my_entity",
    entity_id=row.id,
    description=f"Created my_entity: {row.name}"
)
db.add(db_event)
db.commit()
```

Commit the event in a separate `db.commit()` after the main record commit so that event failures do not roll back the primary write.

### 7. Prometheus Metrics — Do Not Duplicate

Before defining new metrics, grep for existing metric names to avoid `ValueError: Duplicated timeseries` on startup:

```bash
grep -r "Counter\|Histogram\|Gauge" registry/ --include="*.py" -l
```

If a counter or histogram already exists at the process level (e.g., the `registry_write_latency` histogram in `api.py`), reuse it by importing from the module that defines it or use a distinct prefix scoped to the new router.

### 8. Error Handling Standards

- `404 Not Found` — resource does not exist
- `409 Conflict` — duplicate unique constraint violation (catch `IntegrityError` from sqlalchemy.exc)
- `422 Unprocessable Entity` — FastAPI raises automatically for Pydantic validation failures; do not catch these
- `500 Internal Server Error` — all other unexpected exceptions; always log the exception before raising

Never swallow exceptions silently. Every except clause either re-raises or raises `HTTPException`.

### 9. Testing Requirements

Write a `pytest` test for every new endpoint. Tests go in `registry/tests/` or alongside the module as `test_<module>.py`.

Minimal test structure using `TestClient`:

```python
from fastapi.testclient import TestClient
from api import app
import pytest

client = TestClient(app)

def test_create_entity_returns_201():
    payload = {"name": "test", "meta_data": None}
    response = client.post("/api/v1/my-resource/", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "test"

def test_get_entity_404_when_missing():
    import uuid
    response = client.get(f"/api/v1/my-resource/{uuid.uuid4()}")
    assert response.status_code == 404
```

Use `pytest-mock` to patch `get_db` for unit tests that should not hit PostgreSQL.

### 10. Verification

After implementing, state the verification steps that must pass:

1. `docker compose exec dhg-registry-api python -c "from <module> import router; print('import OK')"` — confirms no import errors
2. `curl -s http://localhost:8000/healthz` → `OK` — confirms DB connectivity survives the new code
3. `curl -s http://localhost:8000/metrics | grep <new_metric_name>` — confirms Prometheus metrics registered
4. `curl -s -X POST http://localhost:8000/api/v1/<resource>/ -H 'Content-Type: application/json' -d '<minimal payload>'` — confirms the happy path
5. `curl -s http://localhost:8000/docs` → HTTP 200 — confirms OpenAPI schema generation succeeds

## Constraints and Non-Negotiables

- No placeholders, TODOs, or `pass` in production code — every function must be complete
- No raw hex colors or inline styles if generating any frontend HTML — use DHG CSS tokens
- All container references use the `dhg-` prefix; internal service URLs use `dhgaifactory35_dhg-network` DNS names
- `AI_FACTORY_REGISTRY_URL` inside containers must point to `http://dhg-registry-api:8000`, never `localhost:8500`
- Do not use `from __future__ import annotations` — it breaks SQLAlchemy column introspection in some versions
- Do not modify the WebSocket endpoint on port 8011 — it is deprecated and slated for replacement
- LangGraph is the sole orchestration platform; do not add Node-RED integrations or reference the legacy `agents/` directory

## Quick Reference — DHG Registry Entities

| Model | Table | Key FKs |
|---|---|---|
| Media | media | — |
| Transcript | transcripts | media_id → media.id |
| Segment | segments | transcript_id → transcripts.id |
| Event | events | entity_id (nullable, any entity) |
| Agent | agents | — |
| AgentHeartbeat | agent_heartbeats | agent_id → agents.id |
| Project | projects | — |
| Conversation | conversations | project_id → projects.id |
| Message | messages | conversation_id → conversations.id |
| Artifact | artifacts | conversation_id → conversations.id |

## Common Pitfalls in This Codebase

- `api.py` uses a synchronous `create_engine` + `SessionLocal`; do not replace with `AsyncSession` without migrating all existing endpoints — add async sessions only in new isolated router files if needed
- Pydantic `UUID4` is imported but `uuid.UUID` is the correct annotation for SQLAlchemy UUID columns — use `uuid.UUID` in schemas
- The `meta_data` column name (not `metadata`) avoids conflict with SQLAlchemy's reserved `metadata` attribute — follow this naming convention
- `db.refresh(row)` is required after `db.commit()` to repopulate server-generated fields (`id`, `created_at`)
- Import order in `api.py`: routers are imported after `app = FastAPI(...)` to avoid circular imports with `database.py`
