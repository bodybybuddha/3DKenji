import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

# MUST set DATABASE_URL before any app modules load
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

# Initialize database tables at module import time
from backend.db.base import Base
from backend.db import get_engine

_engine = get_engine()
Base.metadata.create_all(_engine)


@pytest.fixture(scope="session", autouse=True)
def _start_api_server():
    project_root = Path(__file__).resolve().parents[1]
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        _, port = sock.getsockname()
    base_url = f"http://127.0.0.1:{port}"
    os.environ["API_BASE_URL"] = base_url
    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "backend.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    process = subprocess.Popen(cmd, cwd=project_root)
    try:
        for _ in range(30):
            try:
                resp = httpx.get(f"{base_url}/api/v1/health", timeout=1.0)
                if resp.status_code == 200:
                    yield
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.2)
        raise RuntimeError("API server did not start in time")
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
