import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.core import oauth_state
from backend.db import get_db
from backend.main import create_app
from backend.models.app_setting import AppSetting
from backend.services.app_settings_service import AppSettingsService


@pytest.fixture(autouse=True)
def clear_oauth_state_store():
    oauth_state._state_store.clear()
    yield
    oauth_state._state_store.clear()


@pytest.fixture
def client(db_session):
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _save_oauth_settings(db_session, **overrides):
    payload = {
        "enabled": True,
        "provider_name": "oidc",
        "issuer_url": "https://auth.example.com/application/o/3dkenji/",
        "client_id": "kenji-client",
        "client_secret": "super-secret",
        "callback_url": "https://3dkenji.example.com/api/v1/auth/oauth/oidc/callback",
        "scopes": "openid email profile",
        "cookie_secure": True,
    }
    payload.update(overrides)
    AppSettingsService(db_session).update_oauth_settings(payload, updated_by="admin-user")


def test_oauth_authorize_returns_404_when_oauth_disabled(client, db_session):
    db_session.execute(delete(AppSetting).where(AppSetting.key == "oauth"))
    db_session.commit()

    response = client.get("/api/v1/auth/oauth/oidc/authorize", follow_redirects=False)

    assert response.status_code == 404
    assert response.json()["detail"] == "OAuth is not enabled"


def test_oauth_authorize_rejects_unknown_provider_when_enabled(client, db_session):
    _save_oauth_settings(db_session)

    response = client.get(
        "/api/v1/auth/oauth/unknown_provider/authorize",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "Unknown OAuth provider" in response.json()["detail"]


def test_oauth_callback_requires_code_and_state(client, db_session):
    _save_oauth_settings(db_session)

    response = client.get("/api/v1/auth/oauth/oidc/callback", follow_redirects=False)

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing code or state parameter"


def test_oauth_callback_rejects_invalid_state(client, db_session):
    _save_oauth_settings(db_session)

    response = client.get(
        "/api/v1/auth/oauth/oidc/callback?code=test-code&state=missing-state",
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired state"