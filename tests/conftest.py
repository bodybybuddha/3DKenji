import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Use absolute path for test database so subprocess can find it
project_root = Path(__file__).resolve().parents[1]
test_dir = Path(__file__).resolve().parent
test_db_path = test_dir / "test.db"

# MUST set DATABASE_URL before any app modules load
os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"

# Clean up old test database to ensure fresh start
if test_db_path.exists():
    test_db_path.unlink()

# Initialize database tables at module import time
from backend.db.base import Base
from backend.db import get_engine

_engine = get_engine()
Base.metadata.create_all(_engine)


@pytest.fixture(scope="session")
def db_engine():
    """
    Session-scoped database engine.
    
    Creates database schema once per test session.
    All tests share the same database file but use transactions for isolation.
    """
    engine = create_engine(
        f"sqlite:///{test_db_path}",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Function-scoped database session with automatic rollback.
    
    Each test gets a fresh transaction that is rolled back after the test completes.
    This ensures complete isolation - no test can affect another's data.
    
    Usage:
        def test_something(db_session):
            user = User(username="test")
            db_session.add(user)
            db_session.commit()
            # Transaction automatically rolled back after test
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection)()
    
    yield session
    
    # Cleanup: rollback transaction and close connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="session", autouse=True)
def _start_api_server():
    """Start API server for contract tests with proper test database."""
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        _, port = sock.getsockname()
    base_url = f"http://127.0.0.1:{port}"
    os.environ["API_BASE_URL"] = base_url
    
    # Prepare environment for subprocess with test database
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{test_db_path}"
    env["ENABLE_FILE_LOGGING"] = "false"
    
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
    process = subprocess.Popen(
        cmd, 
        cwd=project_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    try:
        for i in range(30):
            try:
                resp = httpx.get(f"{base_url}/api/v1/health", timeout=1.0)
                if resp.status_code == 200:
                    yield
                    return
            except httpx.HTTPError:
                pass
            # Check if process died
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise RuntimeError(f"API server died. Stdout: {stdout}, Stderr: {stderr}")
            time.sleep(0.2)
        # If we get here, server didn't respond in time
        process.terminate()
        stdout, stderr = process.communicate(timeout=2)
        raise RuntimeError(f"API server did not start in time. Stdout: {stdout}, Stderr: {stderr}")
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
