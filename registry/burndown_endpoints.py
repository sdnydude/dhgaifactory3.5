"""Burndown Lists API endpoints — project-agnostic burndown tracking.

Routes:
  POST   /api/burndown-lists                     create a burndown list
  GET    /api/burndown-lists                     list all (filter by project/status/type)
  GET    /api/burndown-lists/{list_id}           get list with all items + stats
  PATCH  /api/burndown-lists/{list_id}           update list title/description/status
  DELETE /api/burndown-lists/{list_id}           delete list and all items
  POST   /api/burndown-lists/{list_id}/items     bulk-add items
  PATCH  /api/burndown-items/{item_id}           update item status/comment/severity
  DELETE /api/burndown-items/{item_id}           delete an item
  GET    /api/burndown-lists/{list_id}/view      interactive HTML view
"""
import json
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from database import get_db
from burndown_schemas import (
    BurndownListCreate,
    BurndownListResponse,
    BurndownListWithItems,
    BurndownListSummary,
    BurndownListUpdate,
    BurndownItemCreate,
    BurndownItemBulkCreate,
    BurndownItemResponse,
    BurndownItemUpdate,
    VALID_LIST_TYPES,
    VALID_LIST_STATUSES,
    VALID_ITEM_STATUSES,
    VALID_SEVERITIES,
    VALID_RESOLUTIONS,
)
import burndown_service as svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/burndown-lists", tags=["burndown-lists"])
item_router = APIRouter(prefix="/api/burndown-items", tags=["burndown-items"])


@router.post("", response_model=BurndownListResponse, status_code=status.HTTP_201_CREATED)
async def create_burndown_list(
    payload: BurndownListCreate,
    db: Session = Depends(get_db),
) -> BurndownListResponse:
    if payload.list_type not in VALID_LIST_TYPES:
        raise HTTPException(422, f"Invalid list_type. Valid: {sorted(VALID_LIST_TYPES)}")
    row = svc.create_list(db, payload)
    return BurndownListResponse.model_validate(row)


@router.get("")
async def list_burndown_lists(
    project_name: Optional[str] = Query(None),
    list_status: Optional[str] = Query(None, alias="status"),
    list_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> dict:
    rows, total = svc.list_burndowns(
        db, project_name=project_name, status=list_status,
        list_type=list_type, limit=limit, offset=offset,
    )
    summaries = []
    for bl in rows:
        stats = svc.get_list_stats(db, bl.id)
        summaries.append(BurndownListSummary(
            id=bl.id, title=bl.title, project_name=bl.project_name,
            list_type=bl.list_type, status=bl.status,
            created_by=bl.created_by, created_at=bl.created_at,
            total_items=stats["total"], passed=stats["pass"],
            failed=stats["fail"], blocked=stats["blocked"],
            not_started=stats["not_started"], skipped=stats["skipped"],
        ))
    return {"items": [s.model_dump(mode="json") for s in summaries], "total": total}


@router.get("/{list_id}", response_model=BurndownListWithItems)
async def get_burndown_list(
    list_id: UUID,
    db: Session = Depends(get_db),
) -> BurndownListWithItems:
    bl = svc.get_list(db, list_id)
    if not bl:
        raise HTTPException(404, "Burndown list not found")
    stats = svc.get_list_stats(db, list_id)
    resp = BurndownListWithItems.model_validate(bl)
    resp.stats = stats
    return resp


@router.patch("/{list_id}", response_model=BurndownListResponse)
async def update_burndown_list(
    list_id: UUID,
    payload: BurndownListUpdate,
    db: Session = Depends(get_db),
) -> BurndownListResponse:
    if payload.status and payload.status not in VALID_LIST_STATUSES:
        raise HTTPException(422, f"Invalid status. Valid: {sorted(VALID_LIST_STATUSES)}")
    row = svc.update_list(db, list_id, payload)
    if not row:
        raise HTTPException(404, "Burndown list not found")
    return BurndownListResponse.model_validate(row)


@router.delete("/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_burndown_list(
    list_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    if not svc.delete_list(db, list_id):
        raise HTTPException(404, "Burndown list not found")


@router.post("/{list_id}/items", status_code=status.HTTP_201_CREATED)
async def add_burndown_items(
    list_id: UUID,
    payload: BurndownItemBulkCreate,
    db: Session = Depends(get_db),
) -> dict:
    for item in payload.items:
        if item.status not in VALID_ITEM_STATUSES:
            raise HTTPException(422, f"Invalid item status '{item.status}'. Valid: {sorted(VALID_ITEM_STATUSES)}")
        if item.severity not in VALID_SEVERITIES:
            raise HTTPException(422, f"Invalid severity '{item.severity}'. Valid: {sorted(VALID_SEVERITIES)}")
    rows = svc.add_items(db, list_id, payload.items)
    if not rows:
        raise HTTPException(404, "Burndown list not found")
    return {"created": len(rows), "items": [BurndownItemResponse.model_validate(r).model_dump(mode="json") for r in rows]}


@item_router.patch("/{item_id}", response_model=BurndownItemResponse)
async def update_burndown_item(
    item_id: UUID,
    payload: BurndownItemUpdate,
    db: Session = Depends(get_db),
) -> BurndownItemResponse:
    if payload.status and payload.status not in VALID_ITEM_STATUSES:
        raise HTTPException(422, f"Invalid status. Valid: {sorted(VALID_ITEM_STATUSES)}")
    if payload.severity and payload.severity not in VALID_SEVERITIES:
        raise HTTPException(422, f"Invalid severity. Valid: {sorted(VALID_SEVERITIES)}")
    if payload.resolution and payload.resolution not in VALID_RESOLUTIONS:
        raise HTTPException(422, f"Invalid resolution. Valid: {sorted(VALID_RESOLUTIONS)}")
    row = svc.update_item(db, item_id, payload)
    if not row:
        raise HTTPException(404, "Burndown item not found")
    return BurndownItemResponse.model_validate(row)


@item_router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_burndown_item(
    item_id: UUID,
    db: Session = Depends(get_db),
) -> None:
    if not svc.delete_item(db, item_id):
        raise HTTPException(404, "Burndown item not found")


# --- Interactive HTML View ---

STATUS_COLORS = {
    "not_started": "#6b7280",
    "pass": "#22c55e",
    "fail": "#ef4444",
    "blocked": "#f59e0b",
    "skipped": "#8b5cf6",
}

SEVERITY_COLORS = {
    "none": "#9ca3af",
    "low": "#3b82f6",
    "medium": "#f59e0b",
    "high": "#f97316",
    "critical": "#ef4444",
}

RESOLUTION_COLORS = {
    "open": "#6b7280",
    "investigating": "#3b82f6",
    "fixed": "#22c55e",
    "deferred": "#f59e0b",
    "wont_fix": "#8b5cf6",
}


@router.get("/{list_id}/view", response_class=HTMLResponse)
async def view_burndown_list(
    list_id: UUID,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    bl = svc.get_list(db, list_id)
    if not bl:
        raise HTTPException(404, "Burndown list not found")
    stats = svc.get_list_stats(db, list_id)

    status_options = "".join(f'<option value="{s}">{s}</option>' for s in sorted(VALID_ITEM_STATUSES))
    severity_options = "".join(f'<option value="{s}">{s}</option>' for s in sorted(VALID_SEVERITIES))
    resolution_options = "".join(f'<option value="{s}">{s}</option>' for s in sorted(VALID_RESOLUTIONS))

    rows_html = ""
    for item in bl.items:
        sc = STATUS_COLORS.get(item.status, "#6b7280")
        sev_c = SEVERITY_COLORS.get(item.severity, "#9ca3af")
        res_c = RESOLUTION_COLORS.get(item.resolution, "#6b7280")
        url_cell = f'<a href="{item.url}" target="_blank" style="color:#3b82f6">{item.url}</a>' if item.url else ""
        rows_html += f"""<tr data-id="{item.id}">
  <td style="text-align:center">{item.seq}</td>
  <td><strong>{item.feature}</strong></td>
  <td style="font-size:0.85em">{url_cell}</td>
  <td style="font-size:0.85em">{item.what_to_check or ""}</td>
  <td><select class="status-select" onchange="updateItem('{item.id}', 'status', this.value)"
      style="background:{sc};color:#fff;border:none;border-radius:4px;padding:2px 6px;cursor:pointer">
      {status_options.replace(f'value="{item.status}"', f'value="{item.status}" selected')}
  </select></td>
  <td><select class="severity-select" onchange="updateItem('{item.id}', 'severity', this.value)"
      style="background:{sev_c};color:#fff;border:none;border-radius:4px;padding:2px 6px;cursor:pointer">
      {severity_options.replace(f'value="{item.severity}"', f'value="{item.severity}" selected')}
  </select></td>
  <td><textarea rows="2" style="width:100%;font-size:0.85em;border:1px solid #374151;background:#1f2937;color:#e5e7eb;border-radius:4px;padding:4px"
      onblur="updateItem('{item.id}', 'user_comment', this.value)">{item.user_comment or ""}</textarea></td>
  <td><textarea rows="2" style="width:100%;font-size:0.85em;font-family:monospace;border:1px solid #374151;background:#1f2937;color:#fbbf24;border-radius:4px;padding:4px"
      onblur="updateItem('{item.id}', 'console_errors', this.value)">{item.console_errors or ""}</textarea></td>
  <td><textarea rows="2" style="width:100%;font-size:0.85em;border:1px solid #374151;background:#1f2937;color:#a7f3d0;border-radius:4px;padding:4px"
      onblur="updateItem('{item.id}', 'agent_findings', this.value)">{item.agent_findings or ""}</textarea></td>
  <td><textarea rows="2" style="width:100%;font-size:0.85em;border:1px solid #374151;background:#1f2937;color:#bfdbfe;border-radius:4px;padding:4px"
      onblur="updateItem('{item.id}', 'agent_actions', this.value)">{item.agent_actions or ""}</textarea></td>
  <td><select class="resolution-select" onchange="updateItem('{item.id}', 'resolution', this.value)"
      style="background:{res_c};color:#fff;border:none;border-radius:4px;padding:2px 6px;cursor:pointer">
      {resolution_options.replace(f'value="{item.resolution}"', f'value="{item.resolution}" selected')}
  </select></td>
  <td style="font-size:0.8em;color:#9ca3af">{item.fixed_in_commit or ""}</td>
</tr>"""

    progress = stats["progress_pct"]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{bl.title} — Burndown</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Inter, -apple-system, sans-serif; background: #111827; color: #e5e7eb; padding: 20px; }}
  h1 {{ font-size: 1.5em; margin-bottom: 4px; }}
  .meta {{ color: #9ca3af; font-size: 0.9em; margin-bottom: 16px; }}
  .stats-bar {{ display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }}
  .stat {{ background: #1f2937; border-radius: 8px; padding: 8px 16px; text-align: center; min-width: 80px; }}
  .stat .num {{ font-size: 1.4em; font-weight: 700; }}
  .stat .label {{ font-size: 0.75em; color: #9ca3af; text-transform: uppercase; }}
  .progress {{ background: #374151; border-radius: 8px; height: 12px; margin-bottom: 20px; overflow: hidden; }}
  .progress-fill {{ height: 100%; background: linear-gradient(90deg, #22c55e, #16a34a); border-radius: 8px;
      transition: width 0.5s; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.9em; }}
  th {{ background: #1f2937; padding: 8px; text-align: left; position: sticky; top: 0; font-size: 0.8em;
      text-transform: uppercase; color: #9ca3af; border-bottom: 2px solid #374151; }}
  td {{ padding: 6px 8px; border-bottom: 1px solid #1f2937; vertical-align: top; }}
  tr:hover {{ background: #1f293788; }}
  .toast {{ position: fixed; bottom: 20px; right: 20px; background: #22c55e; color: #000; padding: 8px 16px;
      border-radius: 8px; font-weight: 600; opacity: 0; transition: opacity 0.3s; pointer-events: none; }}
  .toast.show {{ opacity: 1; }}
</style>
</head>
<body>
<h1>{bl.title}</h1>
<div class="meta">{bl.project_name} &middot; {bl.list_type} &middot; {bl.status}
  {(" &middot; " + bl.description) if bl.description else ""}</div>

<div class="stats-bar">
  <div class="stat"><div class="num">{stats['total']}</div><div class="label">Total</div></div>
  <div class="stat"><div class="num" style="color:#22c55e">{stats['pass']}</div><div class="label">Pass</div></div>
  <div class="stat"><div class="num" style="color:#ef4444">{stats['fail']}</div><div class="label">Fail</div></div>
  <div class="stat"><div class="num" style="color:#f59e0b">{stats['blocked']}</div><div class="label">Blocked</div></div>
  <div class="stat"><div class="num" style="color:#6b7280">{stats['not_started']}</div><div class="label">Todo</div></div>
  <div class="stat"><div class="num" style="color:#8b5cf6">{stats['skipped']}</div><div class="label">Skip</div></div>
</div>

<div class="progress"><div class="progress-fill" style="width:{progress}%"></div></div>

<table>
<thead><tr>
  <th>#</th><th>Feature</th><th>URL</th><th>What to Check</th>
  <th>Status</th><th>Severity</th><th>Comment</th><th>Console Errors</th>
  <th>Agent Findings</th><th>Agent Actions</th><th>Resolution</th><th>Fixed In</th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>

<div class="toast" id="toast">Saved</div>

<script>
const API = window.location.origin;
const STATUS_COLORS = {json.dumps(STATUS_COLORS)};
const SEVERITY_COLORS = {json.dumps(SEVERITY_COLORS)};
const RESOLUTION_COLORS = {json.dumps(RESOLUTION_COLORS)};

async function updateItem(id, field, value) {{
  try {{
    const res = await fetch(API + '/api/burndown-items/' + id, {{
      method: 'PATCH',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{[field]: value}})
    }});
    if (!res.ok) throw new Error('Save failed');
    const el = document.querySelector(`tr[data-id="${{id}}"]`);
    if (field === 'status') {{
      const sel = el.querySelector('.status-select');
      sel.style.background = STATUS_COLORS[value] || '#6b7280';
    }}
    if (field === 'severity') {{
      const sel = el.querySelector('.severity-select');
      sel.style.background = SEVERITY_COLORS[value] || '#9ca3af';
    }}
    if (field === 'resolution') {{
      const sel = el.querySelector('.resolution-select');
      sel.style.background = RESOLUTION_COLORS[value] || '#6b7280';
    }}
    showToast('Saved');
  }} catch(e) {{ showToast('Error: ' + e.message); }}
}}

function showToast(msg) {{
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 1500);
}}
</script>
</body>
</html>"""
    return HTMLResponse(content=html)
