import uuid

import pytest
from fastapi.testclient import TestClient

from backend.core.auth import create_access_token
from backend.db import get_db
from backend.main import create_app
from backend.services.app_settings_service import AppSettingsService
from backend.services.user_service import UserService


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _create_user(db_session, *, is_admin, password):
    suffix = uuid.uuid4().hex[:8]
    return UserService(db_session).create_user(
        username=f"user_{suffix}",
        email=f"user_{suffix}@example.com",
        display_name=f"User {suffix}",
        password=password,
        is_admin=is_admin,
    )


def _save_oauth_settings(db_session):
    AppSettingsService(db_session).update_oauth_settings(
        {
            "enabled": True,
            "provider_name": "oidc",
            "issuer_url": "https://auth.example.com/application/o/3dkenji/",
            "client_id": "kenji-client",
            "client_secret": "super-secret",
            "callback_url": "https://3dkenji.example.com/api/v1/auth/oauth/oidc/callback",
            "scopes": "openid email profile",
            "cookie_secure": True,
        },
        updated_by="admin-user",
    )


def test_admin_recovery_login_with_valid_admin_credentials_returns_token(client, db_session):
    admin_user = _create_user(db_session, is_admin=True, password="AdminPass123!")

    response = client.post(
        "/api/v1/auth/admin/recovery-login",
        json={"username": admin_user.username, "password": "AdminPass123!"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token"]
    assert payload["user"]["id"] == admin_user.id


def test_admin_recovery_login_rejects_non_admin_user(client, db_session):
    user = _create_user(db_session, is_admin=False, password="UserPass123!")

    response = client.post(
        "/api/v1/auth/admin/recovery-login",
        json={"username": user.username, "password": "UserPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"


def test_admin_recovery_login_rejects_wrong_password(client, db_session):
    admin_user = _create_user(db_session, is_admin=True, password="AdminPass123!")

    response = client.post(
        "/api/v1/auth/admin/recovery-login",
        json={"username": admin_user.username, "password": "WrongPass123!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_admin_recovery_login_rejects_oidc_only_user_without_password(client, db_session):
    oidc_only_admin = _create_user(db_session, is_admin=True, password=None)

    response = client.post(
        "/api/v1/auth/admin/recovery-login",
        json={"username": oidc_only_admin.username, "password": "AnyPass123!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_admin_set_local_password_sets_password_for_admin_without_password(client, db_session):
    admin_user = _create_user(db_session, is_admin=True, password=None)
    token = create_access_token(admin_user.id, admin_user.username).access_token

    response = client.post(
        "/api/v1/auth/admin/set-local-password",
        json={"new_password": "RecoveryPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    verified_user = UserService(db_session).verify_password(
        admin_user.username,
        "RecoveryPass123!",
    )

    assert response.status_code == 200
    assert response.json()["id"] == admin_user.id
    assert verified_user is not None


def test_admin_set_local_password_rejects_non_admin_user(client, db_session):
    user = _create_user(db_session, is_admin=False, password="UserPass123!")
    token = create_access_token(user.id, user.username).access_token

    response = client.post(
        "/api/v1/auth/admin/set-local-password",
        json={"new_password": "RecoveryPass123!"},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin only"


def test_admin_can_save_oauth_settings_in_database(client, db_session):
    admin_user = _create_user(db_session, is_admin=True, password="AdminPass123!")
    token = create_access_token(admin_user.id, admin_user.username).access_token

    response = client.post(
        "/api/v1/admin/settings/oauth",
        data={
            "enabled": "on",
            "provider_name": "oidc",
            "issuer_url": "https://auth.example.com/application/o/3dkenji/",
            "client_id": "kenji-client",
            "client_secret": "super-secret",
            "callback_url": "https://3dkenji.example.com/api/v1/auth/oauth/oidc/callback",
            "scopes": "openid email profile",
            "cookie_secure": "on",
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    saved = AppSettingsService(db_session).get_runtime_oauth_settings()

    assert response.status_code == 200
    assert "OAuth settings saved" in response.text
    assert saved["enabled"] is True
    assert saved["client_secret"] == "super-secret"