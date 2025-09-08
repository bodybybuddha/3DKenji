import httpx


def test_model_get_not_found_or_auth():
    resp = httpx.get("http://localhost:8000/api/v1/models/000")
    assert resp.status_code in (401, 403, 404)
