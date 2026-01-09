"""
DHG AI FACTORY - SCRIBE AGENT
Autonomous agent: Records development activities with hourly timestamps
Operates autonomously with human oversight
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os
import structlog
from datetime import datetime, timedelta
import uuid
import asyncio

logger = structlog.get_logger()

app = FastAPI(
    title="DHG AI Factory - Scribe Agent",
    description="Autonomous activity logging with hourly timestamps",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Config:
    REGISTRY_DB_URL = os.getenv("REGISTRY_DB_URL")
    SCRIBE_INTERVAL_MINUTES = int(os.getenv("SCRIBE_INTERVAL_MINUTES", "60"))
    AUTONOMOUS_MODE = os.getenv("SCRIBE_AUTONOMOUS_MODE", "true").lower() == "true"


config = Config()

activity_log: List[Dict[str, Any]] = []
autonomous_task = None


class ActivityRecord(BaseModel):
    """Single activity record"""
    record_id: str
    timestamp: str
    activity_type: str
    agent: str
    description: str
    details: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None
    status: str = "recorded"


class LogActivityRequest(BaseModel):
    """Request to log an activity"""
    activity_type: str
    agent: str
    description: str
    details: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None


class TimelineRequest(BaseModel):
    """Request for activity timeline"""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    agent_filter: Optional[str] = None
    activity_type_filter: Optional[str] = None
    limit: int = 100


class SummaryRequest(BaseModel):
    """Request for activity summary"""
    period: str = "hourly"
    agent_filter: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent": "scribe",
        "autonomous_mode": config.AUTONOMOUS_MODE,
        "interval_minutes": config.SCRIBE_INTERVAL_MINUTES,
        "records_stored": len(activity_log),
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": [
            "activity_logging",
            "timeline_generation",
            "hourly_summaries",
            "autonomous_recording",
            "human_oversight"
        ]
    }


@app.post("/log", response_model=ActivityRecord)
async def log_activity(request: LogActivityRequest):
    """
    Log a development activity
    
    Called by other agents or manually to record activities
    """
    record_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    record = ActivityRecord(
        record_id=record_id,
        timestamp=timestamp,
        activity_type=request.activity_type,
        agent=request.agent,
        description=request.description,
        details=request.details,
        duration_seconds=request.duration_seconds,
        status="recorded"
    )
    
    activity_log.append(record.dict())
    
    logger.info("activity_logged", 
                record_id=record_id, 
                agent=request.agent, 
                activity_type=request.activity_type)
    
    return record


@app.get("/timeline")
async def get_timeline(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    agent_filter: Optional[str] = None,
    limit: int = 100
):
    """
    Get activity timeline
    
    Returns chronological list of activities
    """
    filtered = activity_log.copy()
    
    if agent_filter:
        filtered = [r for r in filtered if r.get("agent") == agent_filter]
    
    if start_time:
        filtered = [r for r in filtered if r.get("timestamp", "") >= start_time]
    
    if end_time:
        filtered = [r for r in filtered if r.get("timestamp", "") <= end_time]
    
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "timeline": filtered[:limit],
        "total_records": len(filtered),
        "generated_at": datetime.utcnow().isoformat()
    }


@app.get("/summary")
async def get_summary(period: str = "hourly", agent_filter: Optional[str] = None):
    """
    Get activity summary
    
    Aggregates activities by time period
    """
    now = datetime.utcnow()
    
    if period == "hourly":
        start = now - timedelta(hours=1)
    elif period == "daily":
        start = now - timedelta(days=1)
    elif period == "weekly":
        start = now - timedelta(weeks=1)
    else:
        start = now - timedelta(hours=1)
    
    start_str = start.isoformat()
    
    filtered = [r for r in activity_log if r.get("timestamp", "") >= start_str]
    
    if agent_filter:
        filtered = [r for r in filtered if r.get("agent") == agent_filter]
    
    by_agent = {}
    by_type = {}
    
    for record in filtered:
        agent = record.get("agent", "unknown")
        activity_type = record.get("activity_type", "unknown")
        
        by_agent[agent] = by_agent.get(agent, 0) + 1
        by_type[activity_type] = by_type.get(activity_type, 0) + 1
    
    return {
        "period": period,
        "start_time": start_str,
        "end_time": now.isoformat(),
        "total_activities": len(filtered),
        "by_agent": by_agent,
        "by_type": by_type,
        "highlights": [
            f"{len(filtered)} activities recorded in last {period}",
            f"{len(by_agent)} unique agents active",
            f"Most active type: {max(by_type, key=by_type.get) if by_type else 'N/A'}"
        ],
        "generated_at": now.isoformat()
    }


@app.post("/snapshot")
async def create_snapshot():
    """
    Create hourly activity snapshot
    
    Called autonomously or manually to capture current state
    """
    snapshot_id = str(uuid.uuid4())
    now = datetime.utcnow()
    hour_ago = now - timedelta(hours=1)
    
    recent = [r for r in activity_log if r.get("timestamp", "") >= hour_ago.isoformat()]
    
    by_agent = {}
    for record in recent:
        agent = record.get("agent", "unknown")
        by_agent.setdefault(agent, []).append(record)
    
    snapshot = {
        "snapshot_id": snapshot_id,
        "timestamp": now.isoformat(),
        "period": "1 hour",
        "total_activities": len(recent),
        "agents_active": list(by_agent.keys()),
        "activities_by_agent": {k: len(v) for k, v in by_agent.items()},
        "recent_highlights": [r.get("description", "") for r in recent[:5]]
    }
    
    activity_log.append({
        "record_id": snapshot_id,
        "timestamp": now.isoformat(),
        "activity_type": "snapshot",
        "agent": "scribe",
        "description": f"Hourly snapshot: {len(recent)} activities from {len(by_agent)} agents",
        "details": snapshot,
        "status": "recorded"
    })
    
    logger.info("snapshot_created", snapshot_id=snapshot_id, activities=len(recent))
    
    return snapshot


async def autonomous_logging_task():
    """
    Background task for autonomous hourly logging
    """
    while True:
        await asyncio.sleep(config.SCRIBE_INTERVAL_MINUTES * 60)
        try:
            await create_snapshot()
            logger.info("autonomous_snapshot_completed")
        except Exception as e:
            logger.error("autonomous_snapshot_failed", error=str(e))


@app.post("/start-autonomous")
async def start_autonomous_mode(background_tasks: BackgroundTasks):
    """
    Start autonomous logging mode
    
    Creates hourly snapshots automatically
    """
    global autonomous_task
    
    if autonomous_task is not None:
        return {"status": "already_running", "interval_minutes": config.SCRIBE_INTERVAL_MINUTES}
    
    background_tasks.add_task(autonomous_logging_task)
    autonomous_task = True
    
    logger.info("autonomous_mode_started", interval=config.SCRIBE_INTERVAL_MINUTES)
    
    return {
        "status": "started",
        "interval_minutes": config.SCRIBE_INTERVAL_MINUTES,
        "message": f"Autonomous logging started. Snapshots every {config.SCRIBE_INTERVAL_MINUTES} minutes."
    }


@app.post("/stop-autonomous")
async def stop_autonomous_mode():
    """
    Stop autonomous logging mode
    
    Requires service restart to fully stop background task
    """
    global autonomous_task
    autonomous_task = None
    
    logger.info("autonomous_mode_stopped")
    
    return {
        "status": "stop_requested",
        "message": "Autonomous mode will stop. Full stop requires service restart."
    }


@app.get("/status")
async def get_status():
    """
    Get scribe agent status
    """
    return {
        "agent": "scribe",
        "autonomous_mode": autonomous_task is not None,
        "autonomous_enabled": config.AUTONOMOUS_MODE,
        "interval_minutes": config.SCRIBE_INTERVAL_MINUTES,
        "records_stored": len(activity_log),
        "oldest_record": activity_log[0].get("timestamp") if activity_log else None,
        "newest_record": activity_log[-1].get("timestamp") if activity_log else None,
        "status": "active",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "scribe",
        "description": "Autonomous activity logging with hourly timestamps",
        "mode": "autonomous" if autonomous_task else "passive",
        "endpoints": ["/health", "/log", "/timeline", "/summary", "/snapshot", "/start-autonomous", "/stop-autonomous", "/status"]
    }


@app.on_event("startup")
async def startup_event():
    logger.info("scribe_agent_starting", autonomous_mode=config.AUTONOMOUS_MODE)
    
    activity_log.append({
        "record_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "activity_type": "startup",
        "agent": "scribe",
        "description": "Scribe agent started",
        "status": "recorded"
    })


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("scribe_agent_stopping")
    
    activity_log.append({
        "record_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "activity_type": "shutdown",
        "agent": "scribe",
        "description": "Scribe agent stopping",
        "status": "recorded"
    })
