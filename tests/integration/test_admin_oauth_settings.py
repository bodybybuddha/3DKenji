import os

import requests


def _api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


def _login_admin() -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{_api_base_url()}/api/v1/auth/validate/login",
        data={"username_or_email": "admin", "password": "admin1234"},
        allow_redirects=False,
        timeout=10,
    )
    assert response.status_code == 303, response.text
    return session


def test_admin_can_save_oauth_settings_and_render_on_page():
    session = _login_admin()

    save_response = session.post(
        f"{_api_base_url()}/api/v1/admin/settings/oauth",
        data={
            "enabled": "on",
            "provider_name": "oidc",
            "issuer_url": "https://auth.test.local/application/o/3dkenji/",
            "client_id": "kenji-client",
            "client_secret": "test-secret",
            "callback_url": "https://3dkenji.test.local/api/v1/auth/oauth/oidc/callback",
            "scopes": "openid email profile",
            "cookie_secure": "on",
        },
        timeout=10,
    )
    assert save_response.status_code == 200, save_response.text
    assert "OAuth settings saved" in save_response.text

    page_response = session.get(f"{_api_base_url()}/admin/settings", timeout=10)
    assert page_response.status_code == 200, page_response.text
    assert "OAuth / OIDC Configuration" in page_response.text
    assert "auth.test.local" in page_response.text
    assert "kenji-client" in page_response.text
    assert "A client secret is already stored" in page_response.text