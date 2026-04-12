import os
import uuid

import requests


def _api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


def _auth_headers(username: str = "admin", password: str = "admin1234") -> dict[str, str]:
    response = requests.post(
        f"{_api_base_url()}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _auth_form_session(username: str, password: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{_api_base_url()}/api/v1/auth/validate/login",
        data={"username_or_email": username, "password": password},
        allow_redirects=False,
        timeout=10,
    )
    assert response.status_code == 303, response.text
    return session


def _register_user() -> tuple[str, str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"acct-{suffix}"
    email = f"{username}@example.com"
    password = "Password123!"

    response = requests.post(
        f"{_api_base_url()}/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "display_name": username,
            "password": password,
        },
        timeout=10,
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["user"]["id"]
    return user_id, username, email, password


def test_profile_settings_update_flow_persists_nickname_and_display_name():
    _, username, email, password = _register_user()
    user_session = _auth_form_session(username, password)

    new_nickname = f"nick-{uuid.uuid4().hex[:8]}"
    update = user_session.post(
        f"{_api_base_url()}/settings/profile",
        data={
            "email": email,
            "display_name": "Updated Display",
            "nickname": new_nickname,
        },
        allow_redirects=False,
        timeout=10,
    )
    assert update.status_code == 204, update.text
    assert update.headers.get("HX-Redirect") == "/settings/profile"

    headers = _auth_headers(username, password)
    me = requests.get(f"{_api_base_url()}/api/v1/users/me", headers=headers, timeout=10)
    assert me.status_code == 200, me.text
    payload = me.json()
    assert payload["nickname"] == new_nickname
    assert payload["display_name"] == "Updated Display"


def test_profile_settings_password_update_works_end_to_end():
    _, username, _, password = _register_user()
    user_session = _auth_form_session(username, password)

    new_password = "Password456!"
    update = user_session.post(
        f"{_api_base_url()}/settings/password",
        data={
            "current_password": password,
            "new_password": new_password,
            "new_password_confirm": new_password,
        },
        allow_redirects=False,
        timeout=10,
    )
    assert update.status_code == 200, update.text

    old_login = requests.post(
        f"{_api_base_url()}/api/v1/auth/login",
        json={"username": username, "password": password},
        timeout=10,
    )
    assert old_login.status_code == 401, old_login.text

    new_login = requests.post(
        f"{_api_base_url()}/api/v1/auth/login",
        json={"username": username, "password": new_password},
        timeout=10,
    )
    assert new_login.status_code == 200, new_login.text


def test_admin_user_update_can_manage_nickname_like_profile_owner():
    user_id, username, email, password = _register_user()
    user_headers = _auth_headers(username, password)
    admin_headers = _auth_headers()

    project_create = requests.post(
        f"{_api_base_url()}/api/v1/projects",
        headers=user_headers,
        json={"title": f"Admin Rename {uuid.uuid4().hex[:8]}"},
        timeout=10,
    )
    assert project_create.status_code == 201, project_create.text
    project_id = project_create.json()["id"]

    new_nickname = f"admin-updated-{uuid.uuid4().hex[:8]}"
    admin_update = requests.put(
        f"{_api_base_url()}/api/v1/admin/users/{user_id}",
        headers=admin_headers,
        data={
            "username": username,
            "email": email,
            "display_name": "Managed By Admin",
            "nickname": new_nickname,
            "role": "user",
            "is_active": "true",
            "password": "",
        },
        timeout=10,
    )
    assert admin_update.status_code == 200, admin_update.text

    user_project = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}",
        headers=user_headers,
        timeout=10,
    )
    assert user_project.status_code == 200, user_project.text
    assert user_project.json()["directory_path"].startswith(f"Projects/{new_nickname}/")

    users_html = requests.get(
        f"{_api_base_url()}/api/v1/admin/users?format=html",
        headers=admin_headers,
        timeout=10,
    )
    assert users_html.status_code == 200, users_html.text
    assert new_nickname in users_html.text
