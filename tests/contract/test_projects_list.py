import pytest
import httpx


def test_projects_list_empty():
    resp = httpx.get("http://localhost:8000/api/v1/projects")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
