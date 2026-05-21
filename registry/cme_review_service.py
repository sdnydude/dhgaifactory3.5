"""CME review service — reviewer configuration and review assignments."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session, joinedload

from models import CMEProject, CMEReviewerConfig, CMEReviewAssignment

logger = logging.getLogger(__name__)


def list_reviewers(db: Session, *, active_only: bool = True) -> list[CMEReviewerConfig]:
    query = db.query(CMEReviewerConfig)
    if active_only:
        query = query.filter(CMEReviewerConfig.is_active == True)
    return query.all()


def create_reviewer(
    db: Session,
    email: str,
    display_name: str,
    notify_email: bool = True,
    notify_google_chat: bool = False,
    google_chat_webhook_url: str | None = None,
    max_concurrent_reviews: int = 5,
) -> CMEReviewerConfig | None:
    """Create a reviewer. Returns None if email already exists."""
    existing = db.query(CMEReviewerConfig).filter(
        CMEReviewerConfig.email == email,
    ).first()
    if existing:
        return None

    reviewer = CMEReviewerConfig(
        email=email,
        display_name=display_name,
        notify_email=notify_email,
        notify_google_chat=notify_google_chat,
        google_chat_webhook_url=google_chat_webhook_url,
        max_concurrent_reviews=max_concurrent_reviews,
    )
    db.add(reviewer)
    db.commit()
    db.refresh(reviewer)
    return reviewer


def deactivate_reviewer(db: Session, reviewer_id: str) -> CMEReviewerConfig | None:
    reviewer = db.query(CMEReviewerConfig).filter(
        CMEReviewerConfig.id == reviewer_id,
    ).first()
    if not reviewer:
        return None
    reviewer.is_active = False
    db.commit()
    return reviewer


def submit_for_review(
    db: Session,
    project: CMEProject,
    reviewer_emails: list[str],
) -> list[dict]:
    """Create review assignments. Raises ValueError if a reviewer is not found/inactive."""
    assignments_data = []
    for order, email in enumerate(reviewer_emails, start=1):
        reviewer = db.query(CMEReviewerConfig).filter(
            CMEReviewerConfig.email == email,
            CMEReviewerConfig.is_active == True,
        ).first()
        if not reviewer:
            raise ValueError(f"Reviewer not found or inactive: {email}")

        now = datetime.utcnow()
        sla_hours = 24

        assignment = CMEReviewAssignment(
            project_id=project.id,
            reviewer_id=reviewer.id,
            reviewer_order=order,
            status="active" if order == 1 else "pending",
            assigned_at=now if order == 1 else None,
            sla_deadline=(now + timedelta(hours=sla_hours)) if order == 1 else None,
        )
        db.add(assignment)
        assignments_data.append({
            "email": email,
            "order": order,
            "status": assignment.status,
        })

    project.status = "review"
    project.human_review_status = "pending"
    db.commit()
    return assignments_data


def get_review_status(db: Session, project_id: str) -> list[CMEReviewAssignment]:
    return (
        db.query(CMEReviewAssignment)
        .filter(CMEReviewAssignment.project_id == project_id)
        .order_by(CMEReviewAssignment.reviewer_order)
        .all()
    )


def submit_review(
    db: Session,
    project: CMEProject,
    reviewer_email: str,
    decision: str,
    notes: str | None = None,
    annotations: list | None = None,
) -> dict | None:
    """Submit a review decision. Returns None if no active assignment found."""
    assignment = (
        db.query(CMEReviewAssignment)
        .join(CMEReviewerConfig)
        .filter(
            CMEReviewAssignment.project_id == project.id,
            CMEReviewerConfig.email == reviewer_email,
            CMEReviewAssignment.status == "active",
        )
        .first()
    )
    if not assignment:
        return None

    now = datetime.utcnow()
    assignment.status = decision
    assignment.decision = decision
    assignment.notes = notes
    assignment.annotations = annotations or []
    assignment.completed_at = now

    if decision == "approved":
        next_assignment = (
            db.query(CMEReviewAssignment)
            .filter(
                CMEReviewAssignment.project_id == project.id,
                CMEReviewAssignment.status == "pending",
            )
            .order_by(CMEReviewAssignment.reviewer_order)
            .first()
        )
        if next_assignment:
            next_assignment.status = "active"
            next_assignment.assigned_at = now
            next_assignment.sla_deadline = now + timedelta(hours=24)
        else:
            project.human_review_status = "approved"
            project.status = "complete"
            project.reviewed_at = now
            project.completed_at = now
    else:
        project.human_review_status = "revision_requested"
        project.human_review_notes = notes

    db.commit()
    return {
        "assignment_id": str(assignment.id),
        "project_status": project.status,
    }


def get_my_reviews(
    db: Session,
    reviewer_email: str,
    status_filter: str | None = "active",
) -> list[dict]:
    query = (
        db.query(CMEReviewAssignment)
        .join(CMEReviewerConfig)
        .options(joinedload(CMEReviewAssignment.project))
        .filter(CMEReviewerConfig.email == reviewer_email)
    )
    if status_filter:
        query = query.filter(CMEReviewAssignment.status == status_filter)

    assignments = query.order_by(CMEReviewAssignment.assigned_at).all()

    result = []
    for a in assignments:
        result.append({
            "assignment_id": str(a.id),
            "project_id": str(a.project_id),
            "project_name": a.project.name if a.project else "Unknown",
            "order": a.reviewer_order,
            "status": a.status,
            "assigned_at": a.assigned_at.isoformat() if a.assigned_at else None,
            "sla_deadline": a.sla_deadline.isoformat() if a.sla_deadline else None,
            "hours_remaining": (
                (a.sla_deadline - datetime.utcnow()).total_seconds() / 3600
            ) if a.sla_deadline else None,
        })
    return result
