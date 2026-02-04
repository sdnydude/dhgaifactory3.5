"""
SLA Timeout Handler for CME Review Workflow
============================================
Background task that monitors review assignments and handles timeouts.

Implements:
- R3: 24-hour SLA per reviewer
- R4: Auto-escalate to next reviewer on timeout
- R5: HOLD + daily notifications for final reviewer timeout

Uses APScheduler for in-process scheduling.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
from sqlalchemy.orm import Session

from langsmith import traceable

# Database imports
from database import SessionLocal
from models import CMEProject, CMEReviewAssignment, CMEReviewerConfig

# Notification service
from notification_service import notification_service


async def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@traceable(name="check_sla_timeouts", run_type="chain")
async def check_sla_timeouts():
    """
    Check for SLA timeouts and handle accordingly.
    Runs every 15 minutes.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        
        # Find active assignments past their SLA deadline
        expired_assignments = db.query(CMEReviewAssignment).filter(
            CMEReviewAssignment.status == "active",
            CMEReviewAssignment.sla_deadline < now
        ).all()
        
        for assignment in expired_assignments:
            await handle_timeout(db, assignment)
        
        # Find assignments approaching deadline (4 hours warning)
        warning_threshold = now + timedelta(hours=4)
        warning_assignments = db.query(CMEReviewAssignment).filter(
            CMEReviewAssignment.status == "active",
            CMEReviewAssignment.sla_deadline < warning_threshold,
            CMEReviewAssignment.sla_deadline > now,
            CMEReviewAssignment.reminder_sent_at.is_(None)
        ).all()
        
        for assignment in warning_assignments:
            await send_warning(db, assignment)
        
        db.commit()
        print(f"[TIMEOUT_HANDLER] Checked {len(expired_assignments)} expired, {len(warning_assignments)} warnings")
        
    finally:
        db.close()


@traceable(name="handle_timeout", run_type="chain")
async def handle_timeout(db: Session, assignment: CMEReviewAssignment):
    """Handle a timed-out assignment (R4, R5)."""
    now = datetime.utcnow()
    project = db.query(CMEProject).filter(CMEProject.id == assignment.project_id).first()
    reviewer = db.query(CMEReviewerConfig).filter(CMEReviewerConfig.id == assignment.reviewer_id).first()
    
    if not project or not reviewer:
        return
    
    # Mark current assignment as timeout
    assignment.status = "timeout"
    assignment.completed_at = now
    
    # Check for next reviewer
    next_assignment = db.query(CMEReviewAssignment).filter(
        CMEReviewAssignment.project_id == assignment.project_id,
        CMEReviewAssignment.status == "pending"
    ).order_by(CMEReviewAssignment.reviewer_order).first()
    
    if next_assignment:
        # R4: Escalate to next reviewer
        next_reviewer = db.query(CMEReviewerConfig).filter(
            CMEReviewerConfig.id == next_assignment.reviewer_id
        ).first()
        
        if next_reviewer:
            next_assignment.status = "active"
            next_assignment.assigned_at = now
            next_assignment.sla_deadline = now + timedelta(hours=24)
            
            await notification_service.on_sla_timeout(
                prev_reviewer_email=reviewer.email,
                prev_reviewer_name=reviewer.display_name,
                next_reviewer_email=next_reviewer.email,
                next_reviewer_name=next_reviewer.display_name,
                project_name=project.name,
                project_id=str(project.id),
                webhook_url=next_reviewer.google_chat_webhook_url
            )
            
            print(f"[TIMEOUT_HANDLER] Escalated {project.name} from {reviewer.email} to {next_reviewer.email}")
    else:
        # R5: Final reviewer timeout - set to HOLD
        project.human_review_status = "hold"
        assignment.escalation_sent_at = now
        
        await notification_service.on_final_timeout(
            reviewer_email=reviewer.email,
            reviewer_name=reviewer.display_name,
            project_name=project.name,
            project_id=str(project.id),
            webhook_url=reviewer.google_chat_webhook_url
        )
        
        print(f"[TIMEOUT_HANDLER] Final reviewer timeout - {project.name} set to HOLD")


@traceable(name="send_warning", run_type="chain")
async def send_warning(db: Session, assignment: CMEReviewAssignment):
    """Send SLA warning 4 hours before deadline."""
    now = datetime.utcnow()
    project = db.query(CMEProject).filter(CMEProject.id == assignment.project_id).first()
    reviewer = db.query(CMEReviewerConfig).filter(CMEReviewerConfig.id == assignment.reviewer_id).first()
    
    if not project or not reviewer:
        return
    
    hours_remaining = (assignment.sla_deadline - now).total_seconds() / 3600
    
    await notification_service.on_sla_warning(
        reviewer_email=reviewer.email,
        reviewer_name=reviewer.display_name,
        project_name=project.name,
        project_id=str(project.id),
        hours_remaining=hours_remaining,
        webhook_url=reviewer.google_chat_webhook_url
    )
    
    assignment.reminder_sent_at = now
    print(f"[TIMEOUT_HANDLER] Sent warning to {reviewer.email} for {project.name}")


@traceable(name="send_daily_hold_reminders", run_type="chain")
async def send_daily_hold_reminders():
    """
    Send daily reminders for projects on HOLD (R5).
    Runs once per day.
    """
    db = SessionLocal()
    try:
        # Find projects on hold
        held_projects = db.query(CMEProject).filter(
            CMEProject.human_review_status == "hold"
        ).all()
        
        for project in held_projects:
            # Find the final reviewer (highest order, timed out)
            assignment = db.query(CMEReviewAssignment).filter(
                CMEReviewAssignment.project_id == project.id,
                CMEReviewAssignment.status == "timeout"
            ).order_by(CMEReviewAssignment.reviewer_order.desc()).first()
            
            if assignment:
                reviewer = db.query(CMEReviewerConfig).filter(
                    CMEReviewerConfig.id == assignment.reviewer_id
                ).first()
                
                if reviewer:
                    await notification_service.on_final_timeout(
                        reviewer_email=reviewer.email,
                        reviewer_name=reviewer.display_name,
                        project_name=project.name,
                        project_id=str(project.id),
                        webhook_url=reviewer.google_chat_webhook_url
                    )
        
        print(f"[TIMEOUT_HANDLER] Sent daily HOLD reminders for {len(held_projects)} projects")
        
    finally:
        db.close()


def start_scheduler():
    """
    Start the APScheduler background scheduler.
    Call this from your main application startup.
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.interval import IntervalTrigger
        from apscheduler.triggers.cron import CronTrigger
        
        scheduler = AsyncIOScheduler()
        
        # Check for timeouts every 15 minutes
        scheduler.add_job(
            check_sla_timeouts,
            IntervalTrigger(minutes=15),
            id="check_sla_timeouts",
            replace_existing=True
        )
        
        # Send daily HOLD reminders at 9 AM UTC
        scheduler.add_job(
            send_daily_hold_reminders,
            CronTrigger(hour=9, minute=0),
            id="daily_hold_reminders",
            replace_existing=True
        )
        
        scheduler.start()
        print("[TIMEOUT_HANDLER] Scheduler started")
        return scheduler
        
    except ImportError:
        print("[TIMEOUT_HANDLER] APScheduler not installed. Run: pip install apscheduler")
        return None


if __name__ == "__main__":
    # Manual test run
    asyncio.run(check_sla_timeouts())
