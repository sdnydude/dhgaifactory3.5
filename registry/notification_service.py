"""
Notification Service for CME Review Workflow
=============================================
Handles Email and Google Chat notifications (Decision R6).

Triggers:
- on_review_assigned: Email + Chat to reviewer when assigned
- on_sla_warning: 4 hours before deadline reminder
- on_sla_timeout: Escalate to next reviewer
- on_final_timeout: Daily HOLD notifications
"""

import os
import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from langsmith import traceable


@dataclass
class NotificationConfig:
    """Configuration for notification service."""
    smtp_host: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_user: str = os.getenv("SMTP_USER", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    from_email: str = os.getenv("FROM_EMAIL", "noreply@digitalharmonyai.com")
    google_chat_default_webhook: str = os.getenv("GOOGLE_CHAT_WEBHOOK", "")


config = NotificationConfig()


class EmailSender:
    """Send email notifications via SMTP."""
    
    def __init__(self):
        self.host = config.smtp_host
        self.port = config.smtp_port
        self.user = config.smtp_user
        self.password = config.smtp_password
        self.from_email = config.from_email
    
    @traceable(name="send_email", run_type="tool")
    async def send(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None
    ) -> bool:
        """Send an email notification."""
        if not self.user or not self.password:
            print(f"[EMAIL] Skipped (no SMTP credentials): {to_email} - {subject}")
            return False
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.from_email
            msg["To"] = to_email
            
            # Attach text and HTML versions
            if body_text:
                msg.attach(MIMEText(body_text, "plain"))
            msg.attach(MIMEText(body_html, "html"))
            
            # Send via SMTP
            with smtplib.SMTP(self.host, self.port) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.sendmail(self.from_email, to_email, msg.as_string())
            
            print(f"[EMAIL] Sent: {to_email} - {subject}")
            return True
            
        except Exception as e:
            print(f"[EMAIL] Failed: {to_email} - {e}")
            return False


class GoogleChatSender:
    """Send Google Chat notifications via webhook."""
    
    @traceable(name="send_google_chat", run_type="tool")
    async def send(
        self,
        webhook_url: str,
        message: str,
        card: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a Google Chat notification."""
        if not webhook_url:
            print(f"[CHAT] Skipped (no webhook): {message[:50]}...")
            return False
        
        try:
            payload = {"text": message}
            if card:
                payload["cards"] = [card]
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
            
            print(f"[CHAT] Sent to webhook")
            return True
            
        except Exception as e:
            print(f"[CHAT] Failed: {e}")
            return False


class NotificationService:
    """Main notification service for CME review workflow."""
    
    def __init__(self):
        self.email = EmailSender()
        self.chat = GoogleChatSender()
    
    @traceable(name="notify_review_assigned", run_type="chain")
    async def on_review_assigned(
        self,
        reviewer_email: str,
        reviewer_name: str,
        project_name: str,
        project_id: str,
        sla_deadline: datetime,
        webhook_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """Notify reviewer when assigned to a project (R6)."""
        hours_remaining = (sla_deadline - datetime.utcnow()).total_seconds() / 3600
        review_url = f"https://app.digitalharmonyai.com/cme/review/{project_id}"
        
        # Email notification
        subject = f"[CME Review] New Review Assignment: {project_name}"
        body_html = f"""
        <html>
        <body>
        <h2>New Review Assignment</h2>
        <p>Hi {reviewer_name},</p>
        <p>You have been assigned to review a CME Grant project.</p>
        <table>
            <tr><td><strong>Project:</strong></td><td>{project_name}</td></tr>
            <tr><td><strong>Deadline:</strong></td><td>{sla_deadline.strftime('%Y-%m-%d %H:%M UTC')} ({hours_remaining:.1f} hours)</td></tr>
        </table>
        <p><a href="{review_url}" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Review Now</a></p>
        </body>
        </html>
        """
        
        email_sent = await self.email.send(reviewer_email, subject, body_html)
        
        # Google Chat notification
        chat_message = f"📋 *New Review Assignment*\n\n*Project:* {project_name}\n*Deadline:* {hours_remaining:.1f} hours\n*Reviewer:* {reviewer_name}\n\n{review_url}"
        chat_sent = await self.chat.send(
            webhook_url or config.google_chat_default_webhook,
            chat_message
        )
        
        return {"email": email_sent, "chat": chat_sent}
    
    @traceable(name="notify_sla_warning", run_type="chain")
    async def on_sla_warning(
        self,
        reviewer_email: str,
        reviewer_name: str,
        project_name: str,
        project_id: str,
        hours_remaining: float,
        webhook_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """Send reminder 4 hours before deadline."""
        review_url = f"https://app.digitalharmonyai.com/cme/review/{project_id}"
        
        subject = f"⏰ [REMINDER] Review Due Soon: {project_name}"
        body_html = f"""
        <html>
        <body>
        <h2>⏰ Review Deadline Approaching</h2>
        <p>Hi {reviewer_name},</p>
        <p>Your review for <strong>{project_name}</strong> is due in <strong>{hours_remaining:.1f} hours</strong>.</p>
        <p>If you do not complete the review, it will be escalated to the next reviewer.</p>
        <p><a href="{review_url}" style="background: #FF9800; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Complete Review Now</a></p>
        </body>
        </html>
        """
        
        email_sent = await self.email.send(reviewer_email, subject, body_html)
        
        chat_message = f"⏰ *Review Deadline Approaching*\n\n*Project:* {project_name}\n*Time Remaining:* {hours_remaining:.1f} hours\n*Reviewer:* {reviewer_name}\n\n{review_url}"
        chat_sent = await self.chat.send(
            webhook_url or config.google_chat_default_webhook,
            chat_message
        )
        
        return {"email": email_sent, "chat": chat_sent}
    
    @traceable(name="notify_sla_timeout", run_type="chain")
    async def on_sla_timeout(
        self,
        prev_reviewer_email: str,
        prev_reviewer_name: str,
        next_reviewer_email: str,
        next_reviewer_name: str,
        project_name: str,
        project_id: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """Notify when review is escalated due to timeout (R4)."""
        # Notify previous reviewer
        await self.email.send(
            prev_reviewer_email,
            f"[CME Review] Review Escalated: {project_name}",
            f"<p>Your review for {project_name} has been escalated to {next_reviewer_name} due to SLA timeout.</p>"
        )
        
        # Notify next reviewer
        return await self.on_review_assigned(
            next_reviewer_email,
            next_reviewer_name,
            project_name,
            project_id,
            datetime.utcnow() + timedelta(hours=24),
            webhook_url
        )
    
    @traceable(name="notify_final_timeout", run_type="chain")
    async def on_final_timeout(
        self,
        reviewer_email: str,
        reviewer_name: str,
        project_name: str,
        project_id: str,
        webhook_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """Daily HOLD notification when final reviewer times out (R5)."""
        review_url = f"https://app.digitalharmonyai.com/cme/review/{project_id}"
        
        subject = f"🚨 [HOLD] Final Review Required: {project_name}"
        body_html = f"""
        <html>
        <body>
        <h2>🚨 Project On Hold</h2>
        <p>Hi {reviewer_name},</p>
        <p>The CME Grant project <strong>{project_name}</strong> is on HOLD awaiting your final review.</p>
        <p>As the final reviewer, the project cannot proceed without your approval.</p>
        <p><a href="{review_url}" style="background: #f44336; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Complete Review Now</a></p>
        </body>
        </html>
        """
        
        email_sent = await self.email.send(reviewer_email, subject, body_html)
        
        chat_message = f"🚨 *PROJECT ON HOLD*\n\n*Project:* {project_name}\n*Status:* Awaiting final review\n*Reviewer:* {reviewer_name}\n\n{review_url}"
        chat_sent = await self.chat.send(
            webhook_url or config.google_chat_default_webhook,
            chat_message
        )
        
        return {"email": email_sent, "chat": chat_sent}


# Singleton instance
notification_service = NotificationService()
