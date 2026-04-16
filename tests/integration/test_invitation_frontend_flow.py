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
    username = f"frontinvite-{suffix}"
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
        json={"title": f"Invite Frontend {uuid.uuid4().hex[:8]}"},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invitation_frontend_claim_page_and_submit_flow():
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
    token = invite.json()["token"]

    session = _auth_form_session(invitee_username, invitee_password)

    page = session.get(f"{_api_base_url()}/invitations/{token}", timeout=10)
    assert page.status_code == 200, page.text
    assert "Accept Invitation" in page.text

    submit = session.post(
        f"{_api_base_url()}/invitations/{token}/accept",
        timeout=10,
    )
    assert submit.status_code == 200, submit.text
    assert "Invitation accepted" in submit.text

    collaborator_list = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/collaborators",
        headers=owner_headers,
        timeout=10,
    )
    assert collaborator_list.status_code == 200, collaborator_list.text
    assert any(item["role"] == "viewer" for item in collaborator_list.json())


def test_invitation_frontend_claim_rejects_wrong_logged_in_user():
    owner_headers = _auth_headers()
    project = _create_project(owner_headers)

    invited_username, invited_email, invited_password = _register_user()
    stranger_username, stranger_email, stranger_password = _register_user()

    invite = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        json={"email": invited_email, "role": "viewer", "expires_in_days": 7},
        timeout=10,
    )
    assert invite.status_code == 200, invite.text
    token = invite.json()["token"]

    stranger_session = _auth_form_session(stranger_username, stranger_password)
    denied = stranger_session.post(
        f"{_api_base_url()}/invitations/{token}/accept",
        timeout=10,
    )
    assert denied.status_code == 400, denied.text
    assert "does not match your account" in denied.text

    invited_session = _auth_form_session(invited_username, invited_password)
    accepted = invited_session.post(
        f"{_api_base_url()}/invitations/{token}/accept",
        timeout=10,
    )
    assert accepted.status_code == 200, accepted.text
