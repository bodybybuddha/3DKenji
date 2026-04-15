"""Database-backed application settings service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.core.secret_crypto import decrypt_secret, encrypt_secret
from backend.models.app_setting import AppSetting

SMTP_SETTINGS_KEY = "smtp"
OAUTH_SETTINGS_KEY = "oauth"
MASKED_SECRET = "***configured***"
DEFAULT_SMTP_SETTINGS: dict[str, Any] = {
    "host": "",
    "port": 587,
    "username": "",
    "password": "",
    "from_email": "",
    "from_name": "3DKenji",
    "use_starttls": True,
    "use_tls": False,
    "mock_delivery": False,
}
DEFAULT_OAUTH_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "provider_name": "oidc",
    "issuer_url": "",
    "client_id": "",
    "callback_url": "",
    "scopes": "openid email profile",
    "cookie_secure": False,
    "client_secret": "",
    "client_secret_configured": False,
}


class AppSettingsService:
    """Read/write application settings in app_settings table."""

    def __init__(self, session: Session):
        self.session = session

    def get_setting(self, key: str) -> dict[str, Any]:
        setting = self.session.execute(
            select(AppSetting).where(AppSetting.key == key)
        ).scalar_one_or_none()
        if not setting:
            return {}
        value = setting.value_json or {}
        return value if isinstance(value, dict) else {}

    def upsert_setting(self, key: str, value: dict[str, Any], updated_by: str | None) -> dict[str, Any]:
        setting = self.session.execute(
            select(AppSetting).where(AppSetting.key == key)
        ).scalar_one_or_none()

        if setting:
            setting.value_json = value  # type: ignore[assignment]
            setting.updated_by = updated_by  # type: ignore[assignment]
        else:
            setting = AppSetting(
                id=str(uuid.uuid4()),
                key=key,
                value_json=value,
                updated_by=updated_by,
            )
            self.session.add(setting)

        self.session.commit()
        self.session.refresh(setting)
        stored = setting.value_json or {}
        return stored if isinstance(stored, dict) else {}

    def get_smtp_settings(self) -> dict[str, Any]:
        stored = self.get_setting(SMTP_SETTINGS_KEY)
        merged = DEFAULT_SMTP_SETTINGS.copy()
        merged.update(stored)

        # Normalize types to avoid malformed payload surprises.
        merged["port"] = int(merged.get("port") or DEFAULT_SMTP_SETTINGS["port"])
        merged["use_starttls"] = bool(merged.get("use_starttls"))
        merged["use_tls"] = bool(merged.get("use_tls"))
        merged["mock_delivery"] = bool(merged.get("mock_delivery"))
        return merged

    def update_smtp_settings(self, payload: dict[str, Any], updated_by: str | None) -> dict[str, Any]:
        merged = self.get_smtp_settings()
        merged.update(payload)
        return self.upsert_setting(SMTP_SETTINGS_KEY, merged, updated_by)

    def get_oauth_settings(self, include_secret: bool = False) -> dict[str, Any]:
        stored = self.get_setting(OAUTH_SETTINGS_KEY)
        merged = DEFAULT_OAUTH_SETTINGS.copy()
        merged.update({
            "enabled": bool(stored.get("enabled", merged["enabled"])),
            "provider_name": (stored.get("provider_name") or merged["provider_name"]).strip(),
            "issuer_url": (stored.get("issuer_url") or merged["issuer_url"]).strip(),
            "client_id": (stored.get("client_id") or merged["client_id"]).strip(),
            "callback_url": (stored.get("callback_url") or merged["callback_url"]).strip(),
            "scopes": (stored.get("scopes") or merged["scopes"]).strip(),
            "cookie_secure": bool(stored.get("cookie_secure", merged["cookie_secure"])),
        })

        encrypted_secret = stored.get("client_secret_encrypted") or ""
        merged["client_secret_configured"] = bool(encrypted_secret)
        if include_secret and encrypted_secret:
            merged["client_secret"] = decrypt_secret(encrypted_secret)
        else:
            merged["client_secret"] = ""

        return merged

    def get_runtime_oauth_settings(self) -> dict[str, Any]:
        return self.get_oauth_settings(include_secret=True)

    def update_oauth_settings(self, payload: dict[str, Any], updated_by: str | None) -> dict[str, Any]:
        current = self.get_oauth_settings(include_secret=True)
        current_secret = current.get("client_secret") or ""

        secret_value = payload.get("client_secret")
        clear_secret = bool(payload.get("clear_client_secret"))
        if clear_secret:
            current_secret = ""
        elif isinstance(secret_value, str) and secret_value:
            current_secret = secret_value

        record = {
            "enabled": bool(payload.get("enabled", current["enabled"])),
            "provider_name": str(payload.get("provider_name", current["provider_name"]) or "oidc").strip(),
            "issuer_url": str(payload.get("issuer_url", current["issuer_url"]) or "").strip(),
            "client_id": str(payload.get("client_id", current["client_id"]) or "").strip(),
            "callback_url": str(payload.get("callback_url", current["callback_url"]) or "").strip(),
            "scopes": str(payload.get("scopes", current["scopes"]) or DEFAULT_OAUTH_SETTINGS["scopes"]).strip(),
            "cookie_secure": bool(payload.get("cookie_secure", current["cookie_secure"])),
            "client_secret_encrypted": encrypt_secret(current_secret) if current_secret else "",
        }
        self.upsert_setting(OAUTH_SETTINGS_KEY, record, updated_by)
        return self.get_oauth_settings(include_secret=False)
