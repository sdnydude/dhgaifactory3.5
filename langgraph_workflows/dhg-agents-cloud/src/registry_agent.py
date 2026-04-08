"""
Registry Agent — Data Gateway
==============================
Mediates all agent writes to the DHG Registry API. No LLM calls — pure data
plumbing with validation, idempotency, and structured error handling.

Actions:
  save_citations      — persist verified source references
  save_agent_output   — persist an agent's structured output
  save_document       — persist an immutable document version
  save_workflow_event — record a pipeline status change
  save_review_decision— persist a human review decision
  save_evaluation     — persist quality-gate evaluation metrics

Upstream: any content agent or orchestrator
Downstream: DHG Registry API (FastAPI, port 8011)
"""

import os
import json
import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from langsmith import traceable

from tracing import traced_node

import httpx

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

REGISTRY_API_URL = os.getenv("AI_FACTORY_REGISTRY_URL", "http://dhg-registry-api:8000")
AGENT_TIMEOUT = 60  # seconds per request — registry writes should be fast
HTTP_TIMEOUT = 15  # httpx per-request timeout

VALID_ACTIONS = {
    "save_citations",
    "save_agent_output",
    "save_document",
    "save_workflow_event",
    "save_review_decision",
    "save_evaluation",
}


# =============================================================================
# STATE DEFINITION
# =============================================================================

class RegistryState(TypedDict):
    # === INPUT ===
    action: str                         # one of VALID_ACTIONS
    payload: Dict[str, Any]             # action-specific data
    project_id: str                     # target project UUID
    idempotency_key: str                # caller-provided or auto-generated

    # === PROCESSING ===
    validated: bool                     # set by validate_request
    endpoint: str                       # resolved API endpoint
    http_method: str                    # POST or PUT

    # === OUTPUT ===
    success: bool
    result: Dict[str, Any]             # response from registry API
    failed_writes: List[Dict[str, Any]]  # dead-letter queue for failed items

    # === METADATA ===
    errors: List[str]
    model_used: str
    total_tokens: int
    total_cost: float


# =============================================================================
# ACTION → ENDPOINT ROUTING
# =============================================================================

ACTION_ROUTES = {
    "save_citations": {
        "endpoint": "/api/cme/source-references",
        "method": "POST",
        "required_fields": ["citations"],
        "batch": True,  # payload.citations is a list, each item is a separate POST
    },
    "save_agent_output": {
        "endpoint": "/api/cme/agent-outputs",
        "method": "POST",
        "required_fields": ["agent_name", "content"],
        "batch": False,
    },
    "save_document": {
        "endpoint": "/api/cme/documents",
        "method": "POST",
        "required_fields": ["document_type", "title", "content_text"],
        "batch": False,
    },
    "save_workflow_event": {
        "endpoint": "/api/cme/webhook/pipeline-status",
        "method": "POST",
        "required_fields": ["pipeline_status"],
        "batch": False,
    },
    "save_review_decision": {
        "endpoint_template": "/api/cme/projects/{project_id}/review",
        "method": "POST",
        "required_fields": ["decision"],
        "batch": False,
    },
    "save_evaluation": {
        "endpoint": "/api/cme/agent-outputs",
        "method": "POST",
        "required_fields": ["agent_name", "content"],
        "batch": False,
    },
}


def _generate_idempotency_key(action: str, project_id: str, payload: Dict[str, Any]) -> str:
    """Deterministic hash from action + project + payload for dedup."""
    raw = json.dumps({"action": action, "project_id": project_id, "payload": payload}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


# =============================================================================
# GRAPH NODES
# =============================================================================

@traceable(name="registry_agent.validate_request", run_type="chain")
@traced_node("registry_agent", "validate_request")
async def validate_request_node(state: RegistryState) -> dict:
    """Validate the action, required fields, and resolve the endpoint."""
    action = state.get("action", "")
    payload = state.get("payload", {})
    project_id = state.get("project_id", "")
    errors = list(state.get("errors", []))

    if not action:
        errors.append("Missing required field: action")
        return {"validated": False, "errors": errors}

    if action not in VALID_ACTIONS:
        errors.append(f"Unknown action: {action}. Valid: {', '.join(sorted(VALID_ACTIONS))}")
        return {"validated": False, "errors": errors}

    if not project_id:
        errors.append("Missing required field: project_id")
        return {"validated": False, "errors": errors}

    route = ACTION_ROUTES[action]
    missing = [f for f in route["required_fields"] if f not in payload]
    if missing:
        errors.append(f"Missing payload fields for {action}: {', '.join(missing)}")
        return {"validated": False, "errors": errors}

    # Resolve endpoint (some have project_id in URL)
    if "endpoint_template" in route:
        endpoint = route["endpoint_template"].format(project_id=project_id)
    else:
        endpoint = route["endpoint"]

    # Auto-generate idempotency key if not provided
    idem_key = state.get("idempotency_key", "")
    if not idem_key:
        idem_key = _generate_idempotency_key(action, project_id, payload)

    return {
        "validated": True,
        "endpoint": endpoint,
        "http_method": route["method"],
        "idempotency_key": idem_key,
    }


@traceable(name="registry_agent.execute_save", run_type="chain")
@traced_node("registry_agent", "execute_save")
async def execute_save_node(state: RegistryState) -> dict:
    """Call the Registry API. Handles batch (citations) and single-item saves."""
    if not state.get("validated"):
        return {"success": False, "result": {"error": "Validation failed — skipping save"}}

    action = state["action"]
    payload = state.get("payload", {})
    project_id = state["project_id"]
    endpoint = state["endpoint"]
    http_method = state["http_method"]
    errors = list(state.get("errors", []))
    failed_writes: List[Dict[str, Any]] = []

    route = ACTION_ROUTES[action]
    base_url = REGISTRY_API_URL

    results = []

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            if route.get("batch") and action == "save_citations":
                citations = payload.get("citations", [])
                for cit in citations:
                    ref_id = str(cit.get("pmid") or cit.get("doi") or cit.get("ref_id") or "")
                    body = {
                        "project_id": project_id,
                        "ref_type": cit.get("ref_type", "pubmed" if cit.get("pmid") else "doi"),
                        "ref_id": ref_id,
                        "title": cit.get("title", "Untitled"),
                        "authors": cit.get("authors", ""),
                        "journal": cit.get("journal", ""),
                        "publication_date": cit.get("publication_date"),
                        "url": cit.get("url") or cit.get("doi", ""),
                        "abstract": cit.get("abstract", ""),
                        "cached_content": cit.get("cached_content") or cit,
                        "verification_status": cit.get("verification_status"),
                        "verified_by": cit.get("verified_by", "registry_agent"),
                    }
                    try:
                        resp = await client.post(f"{base_url}{endpoint}", json=body)
                        if resp.status_code in (200, 201):
                            results.append(resp.json())
                        else:
                            failed_writes.append({
                                "ref_id": ref_id,
                                "status_code": resp.status_code,
                                "detail": resp.text[:500],
                            })
                    except Exception as exc:
                        failed_writes.append({"ref_id": ref_id, "error": str(exc)})

            else:
                # Single-item save
                body = {**payload, "project_id": project_id}

                # For workflow events, project_id goes in query params
                if action == "save_workflow_event":
                    params = {"project_id": project_id, "pipeline_status": payload["pipeline_status"]}
                    body = {}
                    resp = await client.post(f"{base_url}{endpoint}", params=params, json=body)
                elif action == "save_evaluation":
                    body = {
                        "project_id": project_id,
                        "agent_name": payload["agent_name"],
                        "output_type": "evaluation",
                        "content": payload["content"],
                        "quality_score": payload.get("quality_score"),
                        "document_text": json.dumps(payload["content"]),
                    }
                    resp = await client.post(f"{base_url}{endpoint}", json=body)
                else:
                    resp = await client.request(http_method, f"{base_url}{endpoint}", json=body)

                if resp.status_code in (200, 201):
                    results.append(resp.json())
                else:
                    failed_writes.append({
                        "action": action,
                        "status_code": resp.status_code,
                        "detail": resp.text[:500],
                    })

    except Exception as exc:
        errors.append(f"Registry connection failed: {exc}")
        failed_writes.append({"action": action, "error": str(exc)})

    saved_count = len(results)
    total_attempted = saved_count + len(failed_writes)

    logger.info(
        "Registry Agent [%s]: saved %d/%d items (project=%s)",
        action, saved_count, total_attempted, project_id,
    )

    return {
        "result": {
            "saved_count": saved_count,
            "failed_count": len(failed_writes),
            "items": results,
        },
        "failed_writes": failed_writes,
        "errors": errors,
    }


@traceable(name="registry_agent.confirm_result", run_type="chain")
@traced_node("registry_agent", "confirm_result")
async def confirm_result_node(state: RegistryState) -> dict:
    """Confirm success/failure and finalize the state."""
    result = state.get("result", {})
    failed = state.get("failed_writes", [])
    errors = list(state.get("errors", []))

    saved = result.get("saved_count", 0)
    failed_count = result.get("failed_count", 0)

    if failed:
        for fw in failed:
            detail = fw.get("detail") or fw.get("error") or "unknown"
            ref_id = fw.get("ref_id") or fw.get("action") or "item"
            errors.append(f"Failed to save {ref_id}: {detail}")

    success = saved > 0 and failed_count == 0

    if saved == 0 and failed_count == 0 and not errors:
        # Nothing to save (e.g. empty citation list) — still a success
        success = True

    return {
        "success": success,
        "errors": errors,
        "model_used": "none",
        "total_tokens": 0,
        "total_cost": 0.0,
    }


# =============================================================================
# GRAPH ASSEMBLY
# =============================================================================

def create_registry_graph():
    """Create the Registry Agent graph."""
    workflow = StateGraph(RegistryState)

    workflow.add_node("validate_request", validate_request_node)
    workflow.add_node("execute_save", execute_save_node)
    workflow.add_node("confirm_result", confirm_result_node)

    workflow.set_entry_point("validate_request")
    workflow.add_edge("validate_request", "execute_save")
    workflow.add_edge("execute_save", "confirm_result")
    workflow.add_edge("confirm_result", END)

    return workflow.compile()


graph = create_registry_graph()
