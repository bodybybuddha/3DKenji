"""Database-backed application settings service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.app_setting import AppSetting

SMTP_SETTINGS_KEY = "smtp"
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

LOG_SETTINGS_KEY = "logging"
DEFAULT_LOG_SETTINGS: dict[str, Any] = {
    "log_level": "INFO",
    "max_size_mb": 10,
    "backup_count": 5,
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

    def get_log_settings(self) -> dict[str, Any]:
        stored = self.get_setting(LOG_SETTINGS_KEY)
        merged = DEFAULT_LOG_SETTINGS.copy()
        merged.update(stored)

        valid_levels = ("DEBUG", "INFO", "WARNING", "ERROR")
        level = str(merged.get("log_level", "INFO")).upper()
        merged["log_level"] = level if level in valid_levels else "INFO"
        merged["max_size_mb"] = max(1, int(merged.get("max_size_mb") or DEFAULT_LOG_SETTINGS["max_size_mb"]))
        merged["backup_count"] = max(1, int(merged.get("backup_count") or DEFAULT_LOG_SETTINGS["backup_count"]))
        return merged

    def update_log_settings(self, payload: dict[str, Any], updated_by: str | None) -> dict[str, Any]:
        merged = self.get_log_settings()
        merged.update(payload)
        return self.upsert_setting(LOG_SETTINGS_KEY, merged, updated_by)
