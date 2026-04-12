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


def test_admin_can_save_smtp_settings_and_render_on_page():
    session = _login_admin()

    save_response = session.post(
        f"{_api_base_url()}/api/v1/admin/settings/smtp",
        data={
            "host": "smtp.test.local",
            "port": "2525",
            "username": "mailer",
            "password": "topsecret",
            "from_email": "no-reply@test.local",
            "from_name": "3DKenji Test",
            "use_starttls": "on",
            "mock_delivery": "on",
        },
        timeout=10,
    )
    assert save_response.status_code == 200, save_response.text
    assert "SMTP settings saved" in save_response.text

    page_response = session.get(f"{_api_base_url()}/admin/settings", timeout=10)
    assert page_response.status_code == 200, page_response.text
    assert "smtp.test.local" in page_response.text
    assert "no-reply@test.local" in page_response.text
    assert "Mock delivery" in page_response.text
