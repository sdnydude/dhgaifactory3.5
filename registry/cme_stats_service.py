"""CME stats service — aggregate telemetry queries for Mission Control dashboard."""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import text

from models import CMEProject

SERVICES = [
    {"name": "incident_service", "domain": "Incident Management"},
    {"name": "bug_fixes_service", "domain": "Bug Fixes (memreg)"},
    {"name": "deferred_items_service", "domain": "Deferred Items (memreg)"},
    {"name": "test_coverage_service", "domain": "Test Coverage (memreg)"},
    {"name": "insights_service", "domain": "Insights (memreg)"},
    {"name": "decision_logs_service", "domain": "Decision Logs (memreg)"},
    {"name": "ship_sessions_service", "domain": "Ship Sessions (memreg)"},
    {"name": "agent_sessions_service", "domain": "Agent Sessions (memreg)"},
    {"name": "memory_metrics_service", "domain": "Memory Metrics"},
    {"name": "webhook_service", "domain": "Webhooks"},
    {"name": "corrections_service", "domain": "Corrections (memreg)"},
    {"name": "frontend_specs_service", "domain": "Frontend Specs"},
    {"name": "research_service", "domain": "Research"},
    {"name": "security_service", "domain": "Security / RBAC"},
    {"name": "export_service", "domain": "Export / PDF"},
    {"name": "claude_service", "domain": "Claude Sessions"},
    {"name": "agent_service", "domain": "Agent Registry"},
    {"name": "antigravity_service", "domain": "Antigravity Chat"},
    {"name": "projects_service", "domain": "Projects"},
    {"name": "dev_changelog_service", "domain": "Dev Changelog"},
    {"name": "doc_pages_service", "domain": "Doc Pages (memreg)"},
    {"name": "kb_service", "domain": "KB Search (memreg)"},
    {"name": "inference_service", "domain": "Inference Routing"},
    {"name": "cme_project_service", "domain": "CME Projects"},
    {"name": "cme_pipeline_service", "domain": "CME Pipeline"},
    {"name": "cme_review_service", "domain": "CME Review"},
    {"name": "cme_sync_service", "domain": "CME Sync"},
    {"name": "cme_search_service", "domain": "CME Search"},
    {"name": "cme_stats_service", "domain": "CME Stats"},
]


def _float_or_none(val: object) -> float | None:
    return float(val) if val is not None else None


def _int_or_zero(val: object) -> int:
    return int(val) if val is not None else 0


def get_pipeline_stats(db: Session) -> dict:
    status_rows = db.execute(text(
        "SELECT status, count(*) as cnt FROM cme_projects GROUP BY status"
    )).fetchall()
    projects_by_status = {r.status: r.cnt for r in status_rows}
    total_projects = sum(projects_by_status.values())

    counts = db.execute(text("""
        SELECT
            (SELECT count(*) FROM cme_pipeline_runs) as runs,
            (SELECT count(*) FROM cme_documents) as docs,
            (SELECT count(*) FROM cme_source_references) as refs
    """)).fetchone()

    agent_rows = db.execute(text("""
        SELECT agent_name, count(*) as cnt,
               round(avg(quality_score)::numeric, 2) as avg_quality
        FROM cme_agent_outputs
        GROUP BY agent_name ORDER BY agent_name
    """)).fetchall()
    agent_completion = [
        {"agent": r.agent_name, "count": r.cnt, "avg_quality": _float_or_none(r.avg_quality)}
        for r in agent_rows
    ]

    doc_rows = db.execute(text("""
        SELECT document_type, count(*) as cnt,
               round(avg(word_count)::numeric, 0) as avg_words,
               round(avg(quality_score)::numeric, 2) as avg_quality
        FROM cme_documents
        GROUP BY document_type ORDER BY count(*) DESC
    """)).fetchall()
    document_throughput = [
        {
            "type": r.document_type,
            "count": r.cnt,
            "avg_words": _int_or_zero(r.avg_words),
            "avg_quality": _float_or_none(r.avg_quality),
        }
        for r in doc_rows
    ]

    avg_run_duration_sec = _float_or_none(db.execute(text("""
        SELECT round(avg(EXTRACT(EPOCH FROM (completed_at - triggered_at)))::numeric, 1)
        FROM cme_pipeline_runs WHERE completed_at IS NOT NULL
    """)).scalar())

    active_projects = (
        db.query(CMEProject)
        .filter(CMEProject.status.in_(["processing", "review"]))
        .all()
    )
    active_pipelines = [
        {
            "project_id": str(p.id),
            "name": p.name,
            "status": p.status,
            "current_agent": p.current_agent,
            "progress_percent": p.progress_percent or 0,
        }
        for p in active_projects
    ]

    return {
        "projects_by_status": projects_by_status,
        "total_projects": total_projects,
        "total_runs": counts.runs if counts else 0,
        "total_documents": counts.docs if counts else 0,
        "total_references": counts.refs if counts else 0,
        "agent_completion": agent_completion,
        "document_throughput": document_throughput,
        "avg_run_duration_sec": avg_run_duration_sec,
        "active_pipelines": active_pipelines,
    }


def get_service_health(db: Session) -> dict:
    db_pool = db.execute(text(
        "SELECT count(*) FROM pg_stat_activity WHERE datname = 'dhg_registry'"
    )).scalar() or 0

    table_rows = db.execute(text("""
        SELECT relname, n_live_tup
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY n_live_tup DESC
    """)).fetchall()
    table_counts = {r.relname: r.n_live_tup for r in table_rows}

    return {
        "service_count": len(SERVICES),
        "services": SERVICES,
        "db_active_connections": db_pool,
        "table_counts": table_counts,
    }
