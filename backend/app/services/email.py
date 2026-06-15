"""
Email service — SMTP via stdlib smtplib (no extra dependencies).
All sends are fire-and-forget via asyncio.to_thread so they never
block the request cycle.
"""
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Optional
import asyncio

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Synchronous SMTP send — always call via asyncio.to_thread.
    Returns True on success, False on failure (never raises).
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("[email] SMTP not configured — skipping send to %s", to_email)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = formataddr((settings.EMAIL_FROM_NAME, settings.EMAIL_FROM))
        msg["To"] = to_email

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, to_email, msg.as_string())

        logger.info("[email] sent '%s' to %s", subject, to_email)
        return True

    except Exception as e:
        logger.error("[email] failed to send to %s: %s", to_email, e)
        return False


async def send_email(to_email: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Async wrapper — non-blocking."""
    if not text_body:
        text_body = subject  # fallback plain text
    return await asyncio.to_thread(_send_smtp, to_email, subject, html_body, text_body)


# ── Templates ─────────────────────────────────────────────────────────────────

async def send_candidate_invite(
    to_email: str,
    candidate_name: str,
    job_title: Optional[str],
    scheduled_at: str,
    zoom_link: Optional[str] = None,
) -> bool:
    subject = f"Your Interview Invitation — {job_title or 'Open Position'}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Interview Invitation</h2>
      <p>Dear {candidate_name},</p>
      <p>You have been invited to an interview for the position of <strong>{job_title or 'Open Position'}</strong>.</p>
      <table style="margin:16px 0">
        <tr><td style="color:#666;padding-right:16px">Date &amp; Time</td><td><strong>{scheduled_at}</strong></td></tr>
        {"<tr><td style='color:#666;padding-right:16px'>Zoom Link</td><td><a href='" + zoom_link + "'>" + zoom_link + "</a></td></tr>" if zoom_link else ""}
      </table>
      <p>Please ensure you are in a quiet, well-lit environment with a stable internet connection.</p>
      <p style="color:#888;font-size:12px">This is an automated message from the Interview Analytics Platform.</p>
    </div>
    """
    text = f"Interview Invitation\n\nDear {candidate_name},\n\nYou are invited for {job_title or 'an open position'} on {scheduled_at}.\n{('Zoom: ' + zoom_link) if zoom_link else ''}"
    return await send_email(to_email, subject, html, text)


async def send_recruiter_session_confirmation(
    to_email: str,
    recruiter_name: str,
    candidate_name: str,
    job_title: Optional[str],
    scheduled_at: str,
    session_id: str,
) -> bool:
    subject = f"Interview Scheduled — {candidate_name}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Interview Scheduled</h2>
      <p>Hi {recruiter_name},</p>
      <p>An interview has been scheduled and is ready for monitoring.</p>
      <table style="margin:16px 0">
        <tr><td style="color:#666;padding-right:16px">Candidate</td><td><strong>{candidate_name}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Position</td><td><strong>{job_title or '—'}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Scheduled</td><td><strong>{scheduled_at}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Session ID</td><td><code>{session_id}</code></td></tr>
      </table>
      <p>You will receive the analytics report once the interview concludes.</p>
      <p style="color:#888;font-size:12px">This is an automated message from the Interview Analytics Platform.</p>
    </div>
    """
    text = f"Interview Scheduled\n\nCandidate: {candidate_name}\nPosition: {job_title or '—'}\nScheduled: {scheduled_at}\nSession ID: {session_id}"
    return await send_email(to_email, subject, html, text)


async def send_panel_invite(
    to_email: str,
    panel_name: str,
    panel_role: Optional[str],
    candidate_name: str,
    job_title: Optional[str],
    scheduled_at: str,
    zoom_link: Optional[str] = None,
) -> bool:
    subject = f"Panel Interview — {candidate_name} for {job_title or 'Open Position'}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Panel Interview Invitation</h2>
      <p>Dear {panel_name},</p>
      <p>You have been added as a <strong>{panel_role or 'Panel Member'}</strong> for the following interview:</p>
      <table style="margin:16px 0">
        <tr><td style="color:#666;padding-right:16px">Candidate</td><td><strong>{candidate_name}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Position</td><td><strong>{job_title or '—'}</strong></td></tr>
        <tr><td style="color:#666;padding-right:16px">Date &amp; Time</td><td><strong>{scheduled_at}</strong></td></tr>
        {"<tr><td style='color:#666;padding-right:16px'>Zoom Link</td><td><a href='" + zoom_link + "'>" + zoom_link + "</a></td></tr>" if zoom_link else ""}
      </table>
      <p style="color:#888;font-size:12px">This is an automated message from the Interview Analytics Platform.</p>
    </div>
    """
    text = f"Panel Interview\n\nYou are invited as {panel_role or 'Panel Member'} for {candidate_name} ({job_title or '—'}) on {scheduled_at}."
    return await send_email(to_email, subject, html, text)


async def send_report_ready(
    to_email: str,
    recipient_name: str,
    candidate_name: str,
    job_title: Optional[str],
    session_id: str,
    dashboard_url: Optional[str] = None,
) -> bool:
    subject = f"Interview Report Ready — {candidate_name}"
    report_link = dashboard_url or f"/report/{session_id}"
    html = f"""
    <div style="font-family:sans-serif;max-width:600px;margin:auto">
      <h2 style="color:#1a1a2e">Interview Report Ready</h2>
      <p>Hi {recipient_name},</p>
      <p>The analytics report for <strong>{candidate_name}</strong> ({job_title or 'Open Position'}) is now available.</p>
      <p style="margin:24px 0">
        <a href="{report_link}"
           style="background:#4f46e5;color:#fff;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:600">
          View Report
        </a>
      </p>
      <p style="color:#888;font-size:12px">This is an automated message from the Interview Analytics Platform.</p>
    </div>
    """
    text = f"Interview Report Ready\n\nThe report for {candidate_name} is available.\nView: {report_link}"
    return await send_email(to_email, subject, html, text)