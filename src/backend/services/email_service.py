"""SMTP email delivery utilities."""

from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage

from sqlalchemy.orm import Session

from backend.models.project import Project
from backend.models.project_invitation import ProjectInvitation
from backend.services.app_settings_service import AppSettingsService

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    """Raised when an email cannot be delivered."""


def send_project_invitation_email(
    session: Session,
    invitation: ProjectInvitation,
    project: Project,
    token: str,
    inviter_name: str,
) -> None:
    """Send project invitation email using configured SMTP settings."""
    settings = AppSettingsService(session).get_smtp_settings()

    mock_via_env = os.environ.get("SMTP_MOCK_DELIVERY", "").lower() in {"1", "true", "yes", "on"}
    mock_delivery = bool(settings.get("mock_delivery")) or mock_via_env
    if mock_delivery:
        logger.info(
            "Mock SMTP delivery enabled; invitation email simulated for %s project=%s",
            invitation.invited_email,
            project.id,
        )
        return

    host = str(settings.get("host") or "").strip()
    port = int(settings.get("port") or 587)
    username = str(settings.get("username") or "").strip()
    password = str(settings.get("password") or "")
    from_email = str(settings.get("from_email") or "").strip()
    from_name = str(settings.get("from_name") or "3DKenji").strip() or "3DKenji"
    use_starttls = bool(settings.get("use_starttls"))
    use_tls = bool(settings.get("use_tls"))

    if not host or not from_email:
        raise EmailDeliveryError("SMTP host and from_email must be configured")

    app_base_url = os.environ.get("APP_BASE_URL", "http://localhost:8000").rstrip("/")
    accept_url = f"{app_base_url}/invitations/{token}"

    message = EmailMessage()
    message["Subject"] = f"Invitation to collaborate on {project.title}"
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = invitation.invited_email
    message.set_content(
        "\n".join(
            [
                f"Hello,",
                "",
                f"{inviter_name} invited you to collaborate on the project '{project.title}'.",
                f"Role: {invitation.role}",
                "",
                "Open this link while signed in to claim the invitation:",
                accept_url,
                "",
                "Token (for API/manual flows):",
                token,
                "",
                f"This invitation expires at: {invitation.expires_at.isoformat()}",
            ]
        )
    )

    try:
        if use_tls:
            with smtplib.SMTP_SSL(host=host, port=port, timeout=10) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message)
            return

        with smtplib.SMTP(host=host, port=port, timeout=10) as smtp:
            if use_starttls:
                smtp.starttls()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except Exception as exc:
        raise EmailDeliveryError(f"Failed to send invitation email: {exc}") from exc
