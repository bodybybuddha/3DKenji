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


def _register_user() -> tuple[str, str, str]:
    suffix = uuid.uuid4().hex[:8]
    username = f"invitee-{suffix}"
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
        json={"title": f"Collab Test {uuid.uuid4().hex[:8]}", "description": "collab flow"},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_invitation_lifecycle_update_and_revoke():
    owner_headers = _auth_headers()
    project = _create_project(owner_headers)

    create_response = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        json={
            "email": "pending-invite@example.com",
            "role": "viewer",
            "expires_in_days": 7,
        },
        timeout=10,
    )
    assert create_response.status_code == 200, create_response.text
    invitation = create_response.json()

    list_response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        timeout=10,
    )
    assert list_response.status_code == 200, list_response.text
    assert any(item["invitation_id"] == invitation["invitation_id"] for item in list_response.json())

    update_response = requests.patch(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations/{invitation['invitation_id']}",
        headers=owner_headers,
        json={"role": "editor"},
        timeout=10,
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["role"] == "editor"

    revoke_response = requests.delete(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations/{invitation['invitation_id']}",
        headers=owner_headers,
        timeout=10,
    )
    assert revoke_response.status_code == 204, revoke_response.text

    all_response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        params={"include_inactive": "true"},
        timeout=10,
    )
    assert all_response.status_code == 200, all_response.text
    revoked = next(item for item in all_response.json() if item["invitation_id"] == invitation["invitation_id"])
    assert revoked["revoked_at"] is not None


def test_accept_invitation_adds_collaborator():
    owner_headers = _auth_headers()
    project = _create_project(owner_headers)

    username, email, password = _register_user()

    create_response = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        json={
            "email": email,
            "role": "viewer",
            "expires_in_days": 7,
        },
        timeout=10,
    )
    assert create_response.status_code == 200, create_response.text
    token = create_response.json()["token"]

    invitee_headers = _auth_headers(username=username, password=password)
    accept_response = requests.post(
        f"{_api_base_url()}/api/v1/projects/invitations/{token}/accept",
        headers=invitee_headers,
        timeout=10,
    )
    assert accept_response.status_code == 200, accept_response.text
    assert accept_response.json()["role"] == "viewer"

    collaborators_response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/collaborators",
        headers=owner_headers,
        timeout=10,
    )
    assert collaborators_response.status_code == 200, collaborators_response.text
    collaborators = collaborators_response.json()
    assert any(item["user_id"] == accept_response.json()["user_id"] for item in collaborators)

    # Explicit role change endpoint for existing collaborator assignment.
    promoted = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/collaborators",
        headers=owner_headers,
        json={"user_id": accept_response.json()["user_id"], "role": "editor"},
        timeout=10,
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "editor"


def test_invitation_claim_rejected_for_wrong_user_even_with_mock_email_delivery():
    owner_headers = _auth_headers()
    project = _create_project(owner_headers)

    invited_username, invited_email, invited_password = _register_user()
    stranger_username, stranger_email, stranger_password = _register_user()

    create_response = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project['id']}/invitations",
        headers=owner_headers,
        json={
            "email": invited_email,
            "role": "viewer",
            "expires_in_days": 7,
        },
        timeout=10,
    )
    assert create_response.status_code == 200, create_response.text
    token = create_response.json()["token"]

    stranger_headers = _auth_headers(username=stranger_username, password=stranger_password)
    denied = requests.post(
        f"{_api_base_url()}/api/v1/projects/invitations/{token}/accept",
        headers=stranger_headers,
        timeout=10,
    )
    assert denied.status_code == 400, denied.text

    invited_headers = _auth_headers(username=invited_username, password=invited_password)
    accepted = requests.post(
        f"{_api_base_url()}/api/v1/projects/invitations/{token}/accept",
        headers=invited_headers,
        timeout=10,
    )
    assert accepted.status_code == 200, accepted.text
