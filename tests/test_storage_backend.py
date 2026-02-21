"""Unit tests for storage backends."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from backend.plugins.storage_local import LocalStorageBackend


@pytest.fixture
def temp_storage_dir():
    """Create a temporary directory for storage tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def storage_backend(temp_storage_dir):
    """Create a LocalStorageBackend instance with temporary storage."""
    return LocalStorageBackend(storage_root=temp_storage_dir)


@pytest.fixture
def temp_source_file():
    """Create a temporary source file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
        f.write("test content")
        path = f.name
    try:
        yield path
    finally:
        Path(path).unlink()


class TestLocalStorageBackend:
    """Tests for LocalStorageBackend implementation."""

    @pytest.mark.asyncio
    async def test_register_initializes_directories(self, storage_backend):
        """Test that register() creates necessary directories."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        assert (Path(storage_backend.storage_root) / "projects").exists()
        assert (Path(storage_backend.storage_root) / "tmp").exists()

    @pytest.mark.asyncio
    async def test_health_check_succeeds(self, storage_backend):
        """Test that health_check() reports healthy status."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        health = await storage_backend.health_check()
        assert health["status"] == "healthy"
        assert "storage_root" in health

    @pytest.mark.asyncio
    async def test_store_file(self, storage_backend, temp_source_file):
        """Test storing a file."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        key = await storage_backend.store(temp_source_file, "projects/123/models/test.txt")
        assert key == "projects/123/models/test.txt"

        # Verify file was stored
        stored_path = Path(storage_backend.storage_root) / key
        assert stored_path.exists()
        assert stored_path.read_text() == "test content"

    @pytest.mark.asyncio
    async def test_store_creates_directories(self, storage_backend, temp_source_file):
        """Test that store() creates parent directories as needed."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        await storage_backend.store(
            temp_source_file, "projects/456/media/sub/dir/file.txt"
        )

        stored_path = (
            Path(storage_backend.storage_root) / "projects/456/media/sub/dir/file.txt"
        )
        assert stored_path.exists()

    @pytest.mark.asyncio
    async def test_store_nonexistent_source_raises_error(self, storage_backend):
        """Test that storing a nonexistent file raises FileNotFoundError."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        with pytest.raises(FileNotFoundError):
            await storage_backend.store("/nonexistent/file.txt", "projects/123/file.txt")

    @pytest.mark.asyncio
    async def test_retrieve_file(self, storage_backend, temp_source_file):
        """Test retrieving a stored file."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        key = await storage_backend.store(
            temp_source_file, "projects/123/models/test.txt"
        )
        content = await storage_backend.retrieve(key)

        assert content == b"test content"

    @pytest.mark.asyncio
    async def test_retrieve_nonexistent_raises_error(self, storage_backend):
        """Test that retrieving nonexistent file raises FileNotFoundError."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        with pytest.raises(FileNotFoundError):
            await storage_backend.retrieve("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_delete_file(self, storage_backend, temp_source_file):
        """Test deleting a stored file."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        key = await storage_backend.store(
            temp_source_file, "projects/123/models/test.txt"
        )
        await storage_backend.delete(key)

        stored_path = Path(storage_backend.storage_root) / key
        assert not stored_path.exists()

    @pytest.mark.asyncio
    async def test_delete_cleans_up_empty_dirs(self, storage_backend, temp_source_file):
        """Test that delete() removes empty parent directories."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        key = await storage_backend.store(
            temp_source_file, "projects/789/models/deep/nested/file.txt"
        )
        await storage_backend.delete(key)

        # Parent directories should be removed
        assert not (Path(storage_backend.storage_root) / "projects/789").exists()

    @pytest.mark.asyncio
    async def test_delete_nonexistent_raises_error(self, storage_backend):
        """Test that deleting nonexistent file raises FileNotFoundError."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        with pytest.raises(FileNotFoundError):
            await storage_backend.delete("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_get_url(self, storage_backend, temp_source_file):
        """Test getting URL for a stored file."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        key = await storage_backend.store(
            temp_source_file, "projects/123/models/test.txt"
        )
        url = await storage_backend.get_url(key)

        assert key in url
        assert Path(url).exists()

    @pytest.mark.asyncio
    async def test_get_url_nonexistent_raises_error(self, storage_backend):
        """Test that getting URL for nonexistent file raises FileNotFoundError."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        with pytest.raises(FileNotFoundError):
            await storage_backend.get_url("nonexistent/file.txt")

    @pytest.mark.asyncio
    async def test_roundtrip_store_retrieve_delete(
        self, storage_backend, temp_source_file
    ):
        """Test full lifecycle: store, retrieve, delete."""
        from fastapi import FastAPI

        app = FastAPI()
        await storage_backend.register(app, config=None)

        key = await storage_backend.store(
            temp_source_file, "projects/test/models/roundtrip.txt"
        )

        # Store and retrieve
        content = await storage_backend.retrieve(key)
        assert content == b"test content"

        # Get URL
        url = await storage_backend.get_url(key)
        assert Path(url).exists()

        # Delete
        await storage_backend.delete(key)
        assert not Path(url).exists()

        # Verify gone
        with pytest.raises(FileNotFoundError):
            await storage_backend.retrieve(key)
