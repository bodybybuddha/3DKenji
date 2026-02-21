import os

import httpx


def test_models_upload_requires_auth():
    # multipart/form-data upload would be tested; expect auth requirement
    base_url = os.environ.get("API_BASE_URL", "http://localhost:8000")
    resp = httpx.post(f"{base_url}/api/v1/projects/000/models", files={})
    assert resp.status_code in (401, 403)
