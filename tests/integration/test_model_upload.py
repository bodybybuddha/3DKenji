import os
import uuid
from pathlib import Path

import requests


def _api_base_url() -> str:
    return os.environ.get("API_BASE_URL", "http://localhost:8000")


def _auth_headers() -> dict[str, str]:
    response = requests.post(
        f"{_api_base_url()}/api/v1/auth/login",
        json={"username": "admin", "password": "admin1234"},
        timeout=10,
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_project(headers: dict[str, str]) -> dict:
    response = requests.post(
        f"{_api_base_url()}/api/v1/projects",
        headers=headers,
        json={
            "title": f"Upload Test {uuid.uuid4().hex[:8]}",
            "description": "model upload regression test",
        },
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_multipart_model_upload_persists_model_and_metadata():
    headers = _auth_headers()
    project = _create_project(headers)
    project_id = project["id"]

    upload_response = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project_id}/models",
        headers=headers,
        data={
            "tags": "prototype,regression",
            "description": "Upload from project modal",
        },
        files={"file": ("regression.stl", b"solid r\\nendsolid r\\n", "application/sla")},
        timeout=10,
    )
    assert upload_response.status_code == 201, upload_response.text
    uploaded = upload_response.json()
    assert uploaded["filename"] == "regression.stl"
    assert uploaded["tags"] == ["prototype", "regression"]
    assert uploaded["custom_metadata"].get("description") == "Upload from project modal"
    expected_prefix = f"Projects/{project['category']}/{project['slug']}/models/"
    assert uploaded["storage_key"].startswith(expected_prefix)

    storage_root = Path(os.environ["STORAGE_ROOT"])
    stored_path = storage_root / uploaded["storage_key"]
    assert stored_path.exists()

    list_response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/models",
        headers=headers,
        timeout=10,
    )
    assert list_response.status_code == 200, list_response.text
    items = list_response.json()["items"]
    assert any(item["filename"] == "regression.stl" for item in items)
