import smtplib
import random
import string
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


def generate_verification_code() -> str:
    return ''.join(random.choices(string.digits, k=6))


def _send(to_email: str, subject: str, html: str) -> None:
    """
    Send via Gmail SMTP. Raises on failure — caller must handle.
    No silent fallback — the code must reach the user's inbox.
    """
    gmail_user = settings.gmail_user
    gmail_pass = settings.gmail_app_password.replace(' ', '')

    if not gmail_user or not gmail_pass:
        raise RuntimeError(
            "Gmail is not configured. Add GMAIL_USER and GMAIL_APP_PASSWORD to backend/.env"
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"LexQuery <{gmail_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(gmail_user, gmail_pass)
            server.sendmail(gmail_user, to_email, msg.as_string())
        logger.info(f"[email] ✓ '{subject}' → {to_email}")
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError(
            "Gmail authentication failed. Check GMAIL_USER and GMAIL_APP_PASSWORD in backend/.env. "
            "Make sure you are using an App Password, not your regular Gmail password."
        )
    except Exception as e:
        raise RuntimeError(f"Failed to send email to {to_email}: {e}")


def _base_template(body: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#F6F3EC;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#FFFFFF;border:1px solid #D6CEBA;border-radius:4px;overflow:hidden;">
    <div style="background:#1A2B4A;padding:22px 32px;display:flex;align-items:center;gap:10px;">
      <div style="width:26px;height:26px;background:rgba(255,255,255,.12);border-radius:3px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;color:white;font-family:Georgia,serif;">L</div>
      <span style="color:white;font-size:16px;font-weight:700;font-family:Georgia,serif;letter-spacing:-.3px;">LexQuery</span>
    </div>
    <div style="padding:32px;">{body}</div>
    <div style="padding:14px 32px;border-top:1px solid #D6CEBA;">
      <p style="font-size:11px;color:#8A8672;margin:0;font-family:monospace;letter-spacing:.04em;">
        LexQuery Ltd · Enterprise Legal Intelligence · UK Data Residency
      </p>
    </div>
  </div>
</body>
</html>"""


def send_verification_email(to_email: str, code: str, full_name: str = "") -> None:
    name = full_name.strip() or "there"
    body = f"""
      <p style="font-family:Georgia,serif;font-size:11px;color:#8A8672;letter-spacing:.1em;text-transform:uppercase;margin:0 0 18px;">Email verification</p>
      <h2 style="font-family:Georgia,serif;font-size:22px;font-weight:500;color:#1A2B4A;margin:0 0 12px;letter-spacing:-.01em;">Verify your email address</h2>
      <p style="font-family:Georgia,serif;font-size:15px;color:#3A4A68;line-height:1.65;margin:0 0 26px;">
        Hi {name}, enter the code below to activate your LexQuery account.
      </p>
      <div style="background:#F6F3EC;border:1px solid #D6CEBA;border-radius:4px;padding:24px;text-align:center;margin:0 0 26px;">
        <span style="font-family:monospace;font-size:42px;font-weight:700;color:#1A2B4A;letter-spacing:10px;">{code}</span>
      </div>
      <p style="font-size:12px;color:#8A8672;margin:0;">This code expires in 10 minutes. If you did not create a LexQuery account, ignore this email.</p>
    """
    _send(to_email, "Your LexQuery verification code", _base_template(body))


def send_welcome_email(to_email: str, full_name: str, tenant_name: str) -> None:
    name = full_name.strip() or "there"
    body = f"""
      <h2 style="font-family:Georgia,serif;font-size:22px;font-weight:500;color:#1A2B4A;margin:0 0 12px;">Welcome to LexQuery, {name}</h2>
      <p style="font-family:Georgia,serif;font-size:15px;color:#3A4A68;line-height:1.65;margin:0 0 14px;">
        Your account for <strong>{tenant_name}</strong> is now active.
      </p>
      <p style="font-family:Georgia,serif;font-size:15px;color:#3A4A68;line-height:1.65;margin:0 0 28px;">
        Upload documents, ask questions in plain English, and get cited answers grounded in the exact source passage.
      </p>
      <a href="http://localhost:3000/dashboard" style="display:inline-block;background:#1A2B4A;color:white;padding:12px 24px;border-radius:3px;text-decoration:none;font-size:13px;font-weight:600;">
        Go to your dashboard →
      </a>
    """
    _send(to_email, f"Welcome to LexQuery — {tenant_name} is ready", _base_template(body))


def send_invite_email(to_email: str, invited_by: str, tenant_name: str, role: str, invite_token: str) -> None:
    role_label = role.replace('_', ' ').title()
    invite_url = f"http://localhost:3000/invite?token={invite_token}"
    body = f"""
      <p style="font-family:Georgia,serif;font-size:11px;color:#8A8672;letter-spacing:.1em;text-transform:uppercase;margin:0 0 18px;">Team invitation</p>
      <h2 style="font-family:Georgia,serif;font-size:22px;font-weight:500;color:#1A2B4A;margin:0 0 12px;">You've been invited to LexQuery</h2>
      <p style="font-family:Georgia,serif;font-size:15px;color:#3A4A68;line-height:1.65;margin:0 0 14px;">
        <strong>{invited_by}</strong> has invited you to join <strong>{tenant_name}</strong> on LexQuery as a <strong>{role_label}</strong>.
      </p>
      <p style="font-family:Georgia,serif;font-size:15px;color:#3A4A68;line-height:1.65;margin:0 0 28px;">
        Click the link below to set your password and access your account. This link expires in 48 hours.
      </p>
      <a href="{invite_url}" style="display:inline-block;background:#1A2B4A;color:white;padding:12px 28px;border-radius:3px;text-decoration:none;font-size:13px;font-weight:600;">
        Accept invitation →
      </a>
      <p style="font-size:12px;color:#8A8672;margin:24px 0 0;">
        If you were not expecting this invitation, you can safely ignore this email.
      </p>
    """
    _send(to_email, f"You've been invited to {tenant_name} on LexQuery", _base_template(body))


def send_password_reset_email(to_email: str, token: str, full_name: str = "") -> None:
    name = full_name.strip() or "there"
    reset_url = f"http://localhost:3000/reset-password?token={token}"
    body = f"""
      <p style="font-family:Georgia,serif;font-size:11px;color:#8A8672;letter-spacing:.1em;text-transform:uppercase;margin:0 0 18px;">Password reset</p>
      <h2 style="font-family:Georgia,serif;font-size:22px;font-weight:500;color:#1A2B4A;margin:0 0 12px;letter-spacing:-.01em;">Reset your password</h2>
      <p style="font-family:Georgia,serif;font-size:15px;color:#3A4A68;line-height:1.65;margin:0 0 26px;">
        Hi {name}, click the button below to set a new password for your LexQuery account.
      </p>
      <a href="{reset_url}" style="display:inline-block;background:#1A2B4A;color:white;padding:12px 28px;border-radius:3px;text-decoration:none;font-size:13px;font-weight:600;margin-bottom:26px;">
        Reset password →
      </a>
      <p style="font-size:12px;color:#8A8672;margin:0;">This link expires in 1 hour. If you did not request a password reset, ignore this email.</p>
    """
    _send(to_email, "Reset your LexQuery password", _base_template(body))