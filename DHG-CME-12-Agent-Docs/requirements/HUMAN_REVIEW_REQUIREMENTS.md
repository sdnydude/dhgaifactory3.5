# Human Review Requirements

> **Version**: 1.0  
> **Last Updated**: 2026-01-31  
> **Status**: Draft  

## Overview

This document specifies the human review workflow for the DHG CME 12-Agent System. Human review is the final gate before grant package finalization.

---

## Reviewer Configuration

### Admin-Assigned Reviewers

| Setting | Value |
|---------|-------|
| **Assignment Method** | Admin-assigned via settings UI |
| **Maximum Reviewers** | 3 per project |
| **Minimum Reviewers** | 1 per project |
| **Reviewer Order** | Sequential (Reviewer 1 → 2 → 3) |

### Settings Schema

```python
class ReviewerConfig(TypedDict):
    project_id: str
    reviewers: List[ReviewerAssignment]  # Ordered list, max 3
    sla_hours: int  # Default: 24
    timeout_action: Literal["auto_approve", "hold"]
    admin_notify_on_timeout: bool  # Default: True
    admin_user_id: str  # User ID to receive timeout notifications


class ReviewerAssignment(TypedDict):
    user_id: str
    email: str
    google_chat_id: str
    order: int  # 1, 2, or 3
    is_final: bool  # True for last reviewer
```

---

## SLA and Timeout Behavior

### Per-Reviewer SLA

| Parameter | Value |
|-----------|-------|
| **SLA Duration** | 24 hours from assignment |
| **Grace Period** | None |
| **Timezone** | UTC for all calculations |

### Timeout Actions

#### Non-Final Reviewers (Reviewer 1, 2)

When a non-final reviewer does not respond within 24 hours:

1. **Auto-approve** the current review stage
2. **Badge the approval** as "Auto-approved by timeout"
3. **Advance** to next reviewer in queue
4. **Notify** the next reviewer with timeout context
5. **Notify admin** via email + Google Chat

```
Status: AUTO_APPROVED_TIMEOUT
Reason: "Reviewer {name} did not respond within 24 hours"
Next Action: Assigned to Reviewer {next_order}
Admin Notified: Yes
```

#### Final Reviewer (Reviewer 3 or last in queue)

When the final reviewer does not respond within 24 hours:

1. **HOLD** the project (do NOT auto-approve)
2. **Send notifications** to:
   - Final reviewer (email + Google Chat)
   - Admin (email + Google Chat)
3. **Repeat notifications** every 24 hours until resolved
4. **Log** all notification attempts

```
Status: HELD_AWAITING_FINAL_REVIEW
Reason: "Final reviewer {name} has not responded"
Escalation: Active (notifications repeating every 24h)
Admin Notified: Yes
```

---

## Notification System

### Channels

| Channel | Integration | Use Case |
|---------|------------|----------|
| **Email** | Gmail API | All notifications |
| **Chat** | Google Workspace Chat API | All notifications |

### Notification Types

#### 1. Review Assignment

**Trigger**: Reviewer assigned or advanced to next reviewer

**Recipients**: Assigned reviewer

**Content**:
```
Subject: [DHG CME] Review Required: {project_name}

You have been assigned to review the following CME grant package:

Project: {project_name}
Therapeutic Area: {therapeutic_area}
Deadline: {deadline_datetime} (24 hours from now)

Review Link: {review_url}

Please complete your review within 24 hours. If no action is taken,
the package will be auto-approved and advanced to the next reviewer.
```

#### 2. Timeout Warning (4 hours before deadline)

**Trigger**: 20 hours elapsed, no response

**Recipients**: Assigned reviewer

**Content**:
```
Subject: [DHG CME] REMINDER: Review Due in 4 Hours - {project_name}

Your review of {project_name} is due in 4 hours.

If no action is taken by {deadline_datetime}, the package will be
auto-approved.

Review Link: {review_url}
```

#### 3. Auto-Approve Notification

**Trigger**: Non-final reviewer timeout

**Recipients**: 
- Next reviewer
- Admin

**Content (Next Reviewer)**:
```
Subject: [DHG CME] Review Assigned (Auto-Approved from Previous) - {project_name}

You have been assigned to review {project_name}.

Note: This package was auto-approved by timeout from the previous reviewer
({previous_reviewer_name}).

Deadline: {deadline_datetime} (24 hours from now)
Review Link: {review_url}
```

**Content (Admin)**:
```
Subject: [DHG CME] Timeout Alert: {project_name}

Reviewer {reviewer_name} did not respond within 24 hours.

Action Taken: Auto-approved, advanced to {next_reviewer_name}
Project: {project_name}
Timestamp: {timestamp}
```

#### 4. Final Reviewer Hold Notification

**Trigger**: Final reviewer timeout (repeats every 24h)

**Recipients**: 
- Final reviewer
- Admin

**Content (Final Reviewer)**:
```
Subject: [URGENT] [DHG CME] Review OVERDUE - {project_name}

Your review of {project_name} is OVERDUE.

This is the final review stage. The project is ON HOLD until you respond.

Overdue By: {hours_overdue} hours
Review Link: {review_url}

Please respond immediately or contact the admin.
```

**Content (Admin)**:
```
Subject: [URGENT] [DHG CME] Final Review HELD - {project_name}

The final review for {project_name} is on hold.

Final Reviewer: {reviewer_name}
Overdue By: {hours_overdue} hours
Notification Attempt: #{attempt_number}

The reviewer has been notified. No auto-approval will occur.
Manual intervention may be required.
```

---

## Review Actions

### Available Actions

| Action | Effect | Next State |
|--------|--------|------------|
| **Approve** | Advances to next reviewer or completes | `APPROVED` / `COMPLETE` |
| **Reject** | Terminates pipeline | `REJECTED` |
| **Request Revision** | Routes back to specified agent | `REVISION_REQUESTED` |

### Revision Routing

When a reviewer requests revision, they specify which agent should address the issue:

| Issue Category | Routes To |
|----------------|-----------|
| Prose quality issues | Grant Writer (Agent 10) |
| Learning objective format | Learning Objectives (Agent 6) |
| Gap evidence insufficient | Gap Analysis (Agent 4) |
| Clinical data concerns | Clinical Practice (Agent 3) |
| Research citations | Research (Agent 2) |
| Compliance concerns | Compliance Review (Agent 12) |

---

## Database Schema

### Tables

```sql
-- Reviewer assignments per project
CREATE TABLE review_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    user_id UUID NOT NULL REFERENCES users(id),
    reviewer_order INT NOT NULL CHECK (reviewer_order BETWEEN 1 AND 3),
    is_final BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    deadline_at TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITH TIME ZONE,
    action VARCHAR(50),  -- approve, reject, revision
    notes TEXT,
    auto_approved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    
    UNIQUE(project_id, reviewer_order)
);

-- Notification log
CREATE TABLE review_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id UUID NOT NULL REFERENCES review_assignments(id),
    notification_type VARCHAR(50) NOT NULL,
    channel VARCHAR(20) NOT NULL,  -- email, google_chat
    recipient_id UUID NOT NULL,
    sent_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    error_message TEXT,
    attempt_number INT NOT NULL DEFAULT 1
);

-- Project review config
CREATE TABLE review_config (
    project_id UUID PRIMARY KEY REFERENCES projects(id),
    sla_hours INT NOT NULL DEFAULT 24,
    admin_user_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### Indexes

```sql
CREATE INDEX idx_review_assignments_status ON review_assignments(status);
CREATE INDEX idx_review_assignments_deadline ON review_assignments(deadline_at);
CREATE INDEX idx_review_notifications_assignment ON review_notifications(assignment_id);
```

---

## Scheduler Service

### Cron Jobs

| Job | Schedule | Action |
|-----|----------|--------|
| **Check Deadlines** | Every 15 minutes | Find overdue reviews, trigger timeouts |
| **Send Reminders** | Every hour | Send 4-hour warning reminders |
| **Repeat Hold Notifications** | Every 24 hours | Re-notify for held final reviews |

### Timeout Checker Pseudocode

```python
async def check_review_deadlines():
    """Run every 15 minutes."""
    
    overdue = await db.query("""
        SELECT * FROM review_assignments
        WHERE status = 'pending'
        AND deadline_at < NOW()
    """)
    
    for assignment in overdue:
        if assignment.is_final:
            await hold_final_review(assignment)
        else:
            await auto_approve_and_advance(assignment)


async def auto_approve_and_advance(assignment):
    """Handle non-final reviewer timeout."""
    
    # Update current assignment
    await db.execute("""
        UPDATE review_assignments
        SET status = 'auto_approved',
            auto_approved = TRUE,
            completed_at = NOW()
        WHERE id = $1
    """, assignment.id)
    
    # Get next reviewer
    next_assignment = await db.query("""
        SELECT * FROM review_assignments
        WHERE project_id = $1
        AND reviewer_order = $2
    """, assignment.project_id, assignment.reviewer_order + 1)
    
    if next_assignment:
        # Activate next reviewer
        await db.execute("""
            UPDATE review_assignments
            SET status = 'pending',
                assigned_at = NOW(),
                deadline_at = NOW() + INTERVAL '24 hours'
            WHERE id = $1
        """, next_assignment.id)
        
        # Notify next reviewer
        await send_notification(
            next_assignment.user_id,
            "review_assignment",
            context={"auto_approved_from": assignment.user_id}
        )
    
    # Notify admin
    admin_id = await get_admin_for_project(assignment.project_id)
    await send_notification(admin_id, "timeout_alert", context=assignment)


async def hold_final_review(assignment):
    """Handle final reviewer timeout."""
    
    # Update to held status
    await db.execute("""
        UPDATE review_assignments
        SET status = 'held'
        WHERE id = $1
    """, assignment.id)
    
    # Notify final reviewer (urgent)
    await send_notification(assignment.user_id, "final_review_overdue")
    
    # Notify admin
    admin_id = await get_admin_for_project(assignment.project_id)
    await send_notification(admin_id, "final_review_held")
```

---

## Google Workspace Integration

### Required APIs

1. **Gmail API** - For sending email notifications
2. **Google Chat API** - For sending chat notifications

### Service Account Setup

```yaml
# Required OAuth2 scopes
scopes:
  - https://www.googleapis.com/auth/gmail.send
  - https://www.googleapis.com/auth/chat.bot

# Environment variables
GOOGLE_SERVICE_ACCOUNT_KEY: /path/to/service-account.json
GOOGLE_CHAT_SPACE_ID: spaces/XXXXXXXXX
GMAIL_SENDER_ADDRESS: cme-notifications@dhg.com
```

### Notification Client

```python
from google.oauth2 import service_account
from googleapiclient.discovery import build

class NotificationClient:
    def __init__(self, service_account_path: str):
        self.credentials = service_account.Credentials.from_service_account_file(
            service_account_path,
            scopes=[
                "https://www.googleapis.com/auth/gmail.send",
                "https://www.googleapis.com/auth/chat.bot"
            ]
        )
        self.gmail = build("gmail", "v1", credentials=self.credentials)
        self.chat = build("chat", "v1", credentials=self.credentials)
    
    async def send_email(self, to: str, subject: str, body: str) -> bool:
        # Implementation
        pass
    
    async def send_chat(self, space_id: str, message: str) -> bool:
        # Implementation
        pass
```

---

## Audit Requirements

### Logged Events

| Event | Data Captured |
|-------|---------------|
| Reviewer assigned | project_id, user_id, order, timestamp |
| Review submitted | assignment_id, action, notes, timestamp |
| Auto-approve triggered | assignment_id, reason, timestamp |
| Hold triggered | assignment_id, timestamp |
| Notification sent | assignment_id, channel, recipient, success, timestamp |
| Notification failed | assignment_id, channel, error, timestamp |

### Retention

- All audit logs retained for **7 years** (regulatory compliance)
- Notifications logs retained for **2 years**

---

## UI Requirements

### Admin Settings Panel

- Assign reviewers to projects (drag-and-drop ordering)
- Set SLA hours (default 24)
- View current review status for all projects
- Manual override: Force-advance or force-hold

### Reviewer Dashboard

- List of pending reviews with deadlines
- Countdown timer showing time remaining
- One-click approve/reject/revision
- Revision routing selector

### Status Badges

| Badge | Color | Meaning |
|-------|-------|---------|
| `Pending` | Yellow | Awaiting review |
| `Approved` | Green | Reviewer approved |
| `Auto-Approved` | Orange | Timeout, auto-advanced |
| `Rejected` | Red | Reviewer rejected |
| `Held` | Purple | Final review overdue |
| `Revision` | Blue | Sent back for changes |
