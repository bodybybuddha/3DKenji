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


def _register_user() -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"invitemgr-{suffix}"
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
    return username, email, password


def _create_project(headers: dict[str, str]) -> dict:
    response = requests.post(
        f"{_api_base_url()}/api/v1/projects",
        headers=headers,
        json={"title": f"Invite Mgmt {uuid.uuid4().hex[:8]}"},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invitee_pending_invitations_page_accept_flow():
    owner_headers = _auth_headers()
    project = _create_project(owner_headers)

    invitee_username, invitee_email, invitee_password = _register_user()

    invite = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        json={"email": invitee_email, "role": "viewer", "expires_in_days": 7},
        timeout=10,
    )
    assert invite.status_code == 200, invite.text
    invitation_id = invite.json()["invitation_id"]

    invitee_session = _auth_form_session(invitee_username, invitee_password)
    pending_page = invitee_session.get(f"{_api_base_url()}/invitations", timeout=10)
    assert pending_page.status_code == 200, pending_page.text
    assert "Pending Invitations" in pending_page.text
    assert project["title"] in pending_page.text

    accept_response = invitee_session.post(
        f"{_api_base_url()}/invitations/id/{invitation_id}/accept",
        allow_redirects=False,
        timeout=10,
    )
    assert accept_response.status_code == 303, accept_response.text

    pending_after = invitee_session.get(f"{_api_base_url()}/invitations", timeout=10)
    assert pending_after.status_code == 200, pending_after.text
    assert project["title"] not in pending_after.text


def test_owner_project_invitation_management_page_lifecycle():
    owner_headers = _auth_headers()
    owner_session = _auth_form_session("admin", "admin1234")

    project = _create_project(owner_headers)

    create_response = owner_session.post(
        f"{_api_base_url()}/project/{project['id']}/invitations",
        data={"email": "owner-manage@example.com", "role": "viewer", "expires_in_days": "7"},
        allow_redirects=False,
        timeout=10,
    )
    assert create_response.status_code == 303, create_response.text

    page = owner_session.get(f"{_api_base_url()}/project/{project['id']}/invitations", timeout=10)
    assert page.status_code == 200, page.text
    assert "Project Members" in page.text
    assert "owner-manage@example.com" in page.text
    assert "Pending Invitation" in page.text

    invitation_list = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        timeout=10,
    )
    assert invitation_list.status_code == 200, invitation_list.text
    invitation_id = invitation_list.json()[0]["invitation_id"]

    update_response = owner_session.post(
        f"{_api_base_url()}/project/{project['id']}/invitations/{invitation_id}/role",
        data={"role": "editor"},
        allow_redirects=False,
        timeout=10,
    )
    assert update_response.status_code == 303, update_response.text

    updated_list = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        timeout=10,
    )
    assert updated_list.status_code == 200, updated_list.text
    assert updated_list.json()[0]["role"] == "editor"

    revoke_response = owner_session.post(
        f"{_api_base_url()}/project/{project['id']}/invitations/{invitation_id}/revoke",
        allow_redirects=False,
        timeout=10,
    )
    assert revoke_response.status_code == 303, revoke_response.text

    all_invites = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        params={"include_inactive": "true"},
        headers=owner_headers,
        timeout=10,
    )
    assert all_invites.status_code == 200, all_invites.text
    assert all_invites.json()[0]["revoked_at"] is not None
