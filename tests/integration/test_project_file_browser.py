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
        json={"title": f"Viewer Test {uuid.uuid4().hex[:8]}", "description": "project file browser test"},
        timeout=10,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _write_project_file(project_payload: dict, relative_path: str, content: bytes) -> None:
    storage_root = Path(os.environ["STORAGE_ROOT"])
    project_root = storage_root / "Projects" / project_payload["category"] / project_payload["slug"]
    target = project_root / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def test_project_file_browser_lists_files_with_viewer_metadata():
    headers = _auth_headers()
    project = _create_project(headers)
    project_id = project["id"]

    _write_project_file(project, "models/cube.stl", b"solid cube\nendsolid cube\n")

    response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files",
        headers=headers,
        params={"path": "models"},
        timeout=10,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload["items"], list)
    stl_item = next((item for item in payload["items"] if item["name"] == "cube.stl"), None)
    assert stl_item is not None
    assert stl_item["extension"] == "stl"
    assert stl_item["viewer"] is None


def test_project_file_preview_returns_fallback_when_no_viewer_plugin():
    headers = _auth_headers()
    project = _create_project(headers)
    project_id = project["id"]

    _write_project_file(project, "models/preview.gcode", b"G1 X10 Y10\n")

    response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files/preview",
        headers=headers,
        params={"path": "models/preview.gcode"},
        timeout=10,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["viewer"] is None
    assert payload["preview_mode"] == "text"
    assert "G1 X10 Y10" in payload["preview_text"]


def test_project_file_browser_rejects_traversal_path():
    headers = _auth_headers()
    project_id = _create_project(headers)["id"]

    response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files",
        headers=headers,
        params={"path": "../../"},
        timeout=10,
    )

    assert response.status_code == 400


def test_project_file_download_returns_binary_content():
    headers = _auth_headers()
    project = _create_project(headers)
    project_id = project["id"]

    expected = b"solid downloadable\nendsolid downloadable\n"
    _write_project_file(project, "models/downloadable.stl", expected)

    response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files/download",
        headers=headers,
        params={"path": "models/downloadable.stl"},
        timeout=10,
    )

    assert response.status_code == 200, response.text
    assert response.content == expected
    assert "attachment; filename=\"downloadable.stl\"" in response.headers.get("Content-Disposition", "")


def test_project_file_upload_endpoint_writes_into_target_directory():
    headers = _auth_headers()
    project = _create_project(headers)
    project_id = project["id"]

    upload_response = requests.post(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files/upload",
        headers=headers,
        data={"path": "models"},
        files={"file": ("uploaded.stl", b"solid uploaded\nendsolid uploaded\n", "application/sla")},
        timeout=10,
    )

    assert upload_response.status_code == 201, upload_response.text
    payload = upload_response.json()
    assert payload["relative_path"] == "models/uploaded.stl"

    list_response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files",
        headers=headers,
        params={"path": "models"},
        timeout=10,
    )
    assert list_response.status_code == 200, list_response.text
    names = [item["name"] for item in list_response.json()["items"]]
    assert "uploaded.stl" in names


def test_project_file_summary_reports_storage_and_counts():
    headers = _auth_headers()
    project = _create_project(headers)
    project_id = project["id"]

    _write_project_file(project, "models/summary.stl", b"solid summary\nendsolid summary\n")
    _write_project_file(project, "cad_files/note.txt", b"hello")

    response = requests.get(
        f"{_api_base_url()}/api/v1/projects/{project_id}/files/summary",
        headers=headers,
        timeout=10,
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["file_count"] >= 2
    assert payload["model_file_count"] >= 1
    assert payload["directory_count"] >= 4
    assert payload["total_size_bytes"] > 0
    assert payload["storage"]["directory_exists"] is True
    assert payload["storage"]["project_info_exists"] is True
    assert payload["storage"]["print_history_exists"] is True