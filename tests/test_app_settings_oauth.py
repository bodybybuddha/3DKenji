from sqlalchemy import select

from backend.models.app_setting import AppSetting
from backend.services.app_settings_service import AppSettingsService


def test_oauth_settings_secret_is_encrypted_at_rest(db_session):
    service = AppSettingsService(db_session)

    service.update_oauth_settings(
        {
            "enabled": True,
            "provider_name": "oidc",
            "issuer_url": "https://auth.example.com/application/o/3dkenji/",
            "client_id": "kenji-client",
            "client_secret": "super-secret-value",
            "callback_url": "https://3dkenji.example.com/api/v1/auth/oauth/oidc/callback",
            "scopes": "openid email profile",
            "cookie_secure": True,
        },
        updated_by="admin-user",
    )

    raw_setting = db_session.execute(
        select(AppSetting).where(AppSetting.key == "oauth")
    ).scalar_one()
    raw_secret = raw_setting.value_json["client_secret_encrypted"]

    masked = service.get_oauth_settings()
    runtime = service.get_runtime_oauth_settings()

    assert raw_secret != "super-secret-value"
    assert masked["client_secret"] == ""
    assert masked["client_secret_configured"] is True
    assert runtime["client_secret"] == "super-secret-value"


def test_oauth_settings_clear_secret_removes_stored_secret(db_session):
    service = AppSettingsService(db_session)

    service.update_oauth_settings(
        {
            "enabled": False,
            "provider_name": "oidc",
            "issuer_url": "https://auth.example.com/application/o/3dkenji/",
            "client_id": "kenji-client",
            "client_secret": "first-secret",
            "callback_url": "https://3dkenji.example.com/api/v1/auth/oauth/oidc/callback",
        },
        updated_by="admin-user",
    )

    cleared = service.update_oauth_settings(
        {
            "enabled": False,
            "provider_name": "oidc",
            "issuer_url": "https://auth.example.com/application/o/3dkenji/",
            "client_id": "kenji-client",
            "client_secret": "",
            "callback_url": "https://3dkenji.example.com/api/v1/auth/oauth/oidc/callback",
            "clear_client_secret": True,
        },
        updated_by="admin-user",
    )

    runtime = service.get_runtime_oauth_settings()

    assert cleared["client_secret_configured"] is False
    assert runtime["client_secret"] == ""