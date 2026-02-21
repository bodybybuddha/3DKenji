import pytest
from fastapi.testclient import TestClient
from backend.main import create_app
import os
import socket
import sqlite3
from urllib.parse import urlparse

def test_hello_world():
    assert 1 + 1 == 2
    

def test_health_endpoint():
    client = TestClient(create_app())
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_database_connectivity():
    # pytest is already imported at top of the file

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        pytest.skip("DATABASE_URL not set; skipping DB connectivity test")

    parsed = urlparse(db_url)
    scheme = (parsed.scheme or "").split("+")[0].lower()

    if scheme in ("sqlite", "sqlite3"):
        # derive sqlite path; urlparse gives path like '/:memory:' or '/absolute/path'
        path = parsed.path or ""
        if path.startswith("/"):
            path = path[1:]
        if not path or path == ":memory:":
            conn = sqlite3.connect(":memory:", timeout=3)
        else:
            conn = sqlite3.connect(path, timeout=3)
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            row = cur.fetchone()
            assert row is not None and row[0] == 1
        finally:
            conn.close()
        return

    host = parsed.hostname
    port = parsed.port

    default_ports = {"postgresql": 5432, "postgres": 5432, "mysql": 3306}
    if port is None:
        port = default_ports.get(scheme)

    if not host or not port:
        pytest.skip(f"Cannot determine host/port for DB URL '{db_url}'; skipping DB connectivity test")

    try:
        sock = socket.create_connection((host, port), timeout=3)
        sock.close()
    except Exception as exc:
        pytest.fail(f"Unable to connect to database at {host}:{port} - {exc}")