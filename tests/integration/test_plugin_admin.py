import os

import requests


def _login_admin(api_base_url: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{api_base_url}/api/v1/auth/validate/login",
        data={"username_or_email": "admin", "password": "admin1234"},
        allow_redirects=False,
    )
    assert response.status_code == 303, response.text
    return session


def test_admin_plugins_page_lists_external_plugins():
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    session = _login_admin(api_base_url)

    response = session.get(f"{api_base_url}/api/v1/admin/plugins")

    assert response.status_code == 200
    assert "Core Themes" in response.text
    assert "settings.yaml" in response.text
    assert "restart" in response.text.lower()


def test_admin_plugin_settings_editor_rejects_invalid_yaml():
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    session = _login_admin(api_base_url)

    response = session.post(
        f"{api_base_url}/api/v1/admin/plugins/core-themes/settings",
        data={"settings_text": "default_theme: [broken\n"},
    )

    assert response.status_code == 400
    assert "Could not save settings.yaml" in response.text


def test_admin_plugin_toggle_persists_disabled_state():
    api_base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    session = _login_admin(api_base_url)

    disable_response = session.post(
        f"{api_base_url}/api/v1/admin/plugins/core-themes/toggle",
        data={"enabled": "false"},
    )

    assert disable_response.status_code == 200
    assert "disabled" in disable_response.text.lower()

    list_response = session.get(f"{api_base_url}/api/v1/admin/plugins")
    assert list_response.status_code == 200
    assert "disabled" in list_response.text.lower()