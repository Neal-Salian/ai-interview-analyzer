"""
SMTP email service — stdlib only, no extra dependencies.
All sends run via asyncio.to_thread (non-blocking).
"""
import smtplib
import logging
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to_email: str, subject: str, html: str, text: str) -> bool:
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("[email] SMTP not configured — skipping send to %s", to_email)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
        msg["To"] = to_email
        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as s:
            s.ehlo()
            s.starttls()
            s.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            s.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())
        logger.info("[email] sent '%s' to %s", subject, to_email)
        return True
    except Exception as e:
        logger.error("[email] failed to send to %s: %s", to_email, e)
        return False


async def send_email(to_email: str, subject: str, html: str, text: str = "") -> bool:
    return await asyncio.to_thread(_send_smtp, to_email, subject, html, text or subject)


async def send_password_reset(to_email: str, recruiter_name: str, reset_url: str) -> bool:
    subject = "Reset your password — Interview Platform"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Password Reset</h2>
      <p>Hi {recruiter_name or 'there'},</p>
      <p>Click the button below to reset your password. This link expires in <strong>30 minutes</strong>.</p>
      <p style="margin:24px 0">
        <a href="{reset_url}"
           style="background:#4f46e5;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
          Reset Password
        </a>
      </p>
      <p>If you did not request this, you can safely ignore this email.</p>
      <p style="color:#888;font-size:12px">This link expires in 30 minutes.</p>
    </div>
    """
    text = f"Reset your password: {reset_url}\n\nThis link expires in 30 minutes."
    return await send_email(to_email, subject, html, text)


async def send_candidate_invite(
    to_email: str, candidate_name: str,
    job_title: Optional[str], scheduled_at: str,
    zoom_link: Optional[str] = None,
) -> bool:
    subject = f"Your Interview Invitation — {job_title or 'Open Position'}"
    zoom_row = f"<tr><td style='color:#666;padding-right:16px'>Meeting Link</td><td><a href='{zoom_link}'>{zoom_link}</a></td></tr>" if zoom_link else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Interview Invitation</h2>
      <p>Dear {candidate_name},</p>
      <p>You have been invited to interview for <strong>{job_title or 'an open position'}</strong>.</p>
      <table style="margin:16px 0">
        <tr><td style="color:#666;padding-right:16px">Date &amp; Time</td><td><strong>{scheduled_at}</strong></td></tr>
        {zoom_row}
      </table>
      <p>Please ensure a quiet, well-lit environment with stable internet.</p>
      <p style="color:#888;font-size:12px">Automated message — Interview Analytics Platform.</p>
    </div>
    """
    return await send_email(to_email, subject, html)


async def send_recruiter_session_confirmation(
    to_email: str, recruiter_name: str, candidate_name: str,
    job_title: Optional[str], scheduled_at: str, session_id: str,
    zoom_start_url: Optional[str] = None,
) -> bool:
    subject = f"Interview Scheduled — {candidate_name}"
    zoom_button = ""
    if zoom_start_url:
        zoom_button = f"""
        <p style="margin:24px 0">
          <a href="{zoom_start_url}"
             style="background:#2d8cff;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
            Start Meeting
          </a>
        </p>
        """
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Interview Scheduled</h2>
      <p>Hi {recruiter_name},</p>
      <table style="margin:16px 0">
        <tr><td style="color:#666;padding-right:16px">Candidate</td><td><strong>{candidate_name}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Position</td><td><strong>{job_title or '—'}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Scheduled</td><td><strong>{scheduled_at}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Session ID</td><td><code>{session_id}</code></td></tr>
      </table>
      {zoom_button}
      <p style="color:#888;font-size:12px">Automated message — Interview Analytics Platform.</p>
    </div>
    """
    return await send_email(to_email, subject, html)


async def send_panel_invite(
    to_email: str, panel_name: str, panel_role: Optional[str],
    candidate_name: str, job_title: Optional[str],
    scheduled_at: str, zoom_link: Optional[str] = None,
) -> bool:
    subject = f"Panel Interview — {candidate_name}"
    zoom_row = f"<tr><td style='color:#666;padding-right:16px'>Meeting Link</td><td><a href='{zoom_link}'>{zoom_link}</a></td></tr>" if zoom_link else ""
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Panel Interview Invitation</h2>
      <p>Dear {panel_name},</p>
      <p>You have been added as <strong>{panel_role or 'Panel Member'}</strong> for:</p>
      <table style="margin:16px 0">
        <tr><td style="color:#666;padding-right:16px">Candidate</td><td><strong>{candidate_name}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Position</td><td><strong>{job_title or '—'}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Date &amp; Time</td><td><strong>{scheduled_at}</strong></td></tr>
        {zoom_row}
      </table>
      <p style="color:#888;font-size:12px">Automated message — Interview Analytics Platform.</p>
    </div>
    """
    return await send_email(to_email, subject, html)


async def send_report_ready(
    to_email: str, recipient_name: str, candidate_name: str,
    job_title: Optional[str], session_id: str,
    dashboard_url: Optional[str] = None,
) -> bool:
    subject = f"Interview Report Ready — {candidate_name}"
    link = dashboard_url or f"{settings.FRONTEND_URL}/sessions/{session_id}/report"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Interview Report Ready</h2>
      <p>Hi {recipient_name},</p>
      <p>The analytics report for <strong>{candidate_name}</strong> ({job_title or 'Open Position'}) is now available.</p>
      <p style="margin:24px 0">
        <a href="{link}"
           style="background:#4f46e5;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
          View Report
        </a>
      </p>
      <p style="color:#888;font-size:12px">Automated message — Interview Analytics Platform.</p>
    </div>
    """
    return await send_email(to_email, subject, html)