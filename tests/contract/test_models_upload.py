import httpx


def test_models_upload_requires_auth():
    # multipart/form-data upload would be tested; expect auth requirement
    resp = httpx.post("http://localhost:8000/api/v1/projects/000/models", files={})
    assert resp.status_code in (401, 403)
