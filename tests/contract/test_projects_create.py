import httpx


def test_projects_create_requires_auth():
    resp = httpx.post("http://localhost:8000/api/v1/projects", json={"title": "Test"})
    # Expect unauthorized until auth is implemented
    assert resp.status_code in (401, 403)
