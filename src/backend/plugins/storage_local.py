"""
Local filesystem storage backend plugin for 3D Kenji.

Stores files in a local directory structure. Useful for development and
single-machine deployments.
"""

import os
import shutil
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI

from backend.core.plugin_interfaces import StorageBackend


class LocalStorageBackend(StorageBackend):
    """
    File system storage backend using local directories.

    Storage structure:
    ```
    STORAGE_ROOT/
        projects/
            {project_id}/
                models/
                    {model_filename}
                media/
                    {media_files}
        tmp/
            {temporary_files}
    ```
    """

    name = "Local Storage"
    version = "1.0.0"
    storage_type = "local"

    def __init__(self, storage_root: Optional[str] = None):
        """
        Initialize local storage backend.

        Args:
            storage_root: Root directory for file storage.
                         Defaults to /workspace/data/storage
        """
        self.storage_root = Path(
            storage_root or os.getenv("STORAGE_ROOT", "/workspace/data/storage")
        )
        # Ensure root directory exists
        self.storage_root.mkdir(parents=True, exist_ok=True)

    async def register(self, app: FastAPI, config: Optional[dict] = None) -> None:
        """
        Initialize storage backend at startup.

        Args:
            app: FastAPI application instance.
            config: Optional plugin configuration.
        """
        # Ensure key directories exist
        (self.storage_root / "projects").mkdir(parents=True, exist_ok=True)
        (self.storage_root / "tmp").mkdir(parents=True, exist_ok=True)

    async def health_check(self) -> dict:
        """
        Check if storage backend is operational.

        Returns:
            Dict with status and optional error message.
        """
        try:
            # Test write permission to root
            test_file = self.storage_root / ".health_check"
            test_file.write_text("ok")
            test_file.unlink()
            return {"status": "healthy", "storage_root": str(self.storage_root)}
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": f"Storage write failed: {str(e)}",
            }

    async def store(self, source_path: str, destination_key: str) -> str:
        """
        Store a file on local filesystem.

        Args:
            source_path: Path to source file to store.
            destination_key: Logical storage key (e.g., "projects/123/models/cube.stl").
                           Will be stored at {storage_root}/{destination_key}

        Returns:
            The destination_key (can be used with retrieve, delete, get_url).

        Raises:
            FileNotFoundError: If source file does not exist.
            IOError: If file copy fails.
        """
        source = Path(source_path)
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        # Build destination path
        dest = self.storage_root / destination_key
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Copy file
        try:
            shutil.copy2(source, dest)
            return destination_key
        except Exception as e:
            raise IOError(f"Failed to store file {destination_key}: {str(e)}")

    async def retrieve(self, storage_key: str) -> bytes:
        """
        Retrieve file contents from local storage.

        Args:
            storage_key: Storage key returned from store().

        Returns:
            File contents as bytes.

        Raises:
            FileNotFoundError: If storage key does not exist.
        """
        path = self.storage_root / storage_key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")

        try:
            return path.read_bytes()
        except Exception as e:
            raise IOError(f"Failed to retrieve file {storage_key}: {str(e)}")

    async def delete(self, storage_key: str) -> None:
        """
        Delete a file from local storage.

        Args:
            storage_key: Storage key returned from store().

        Raises:
            FileNotFoundError: If storage key does not exist.
        """
        path = self.storage_root / storage_key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")

        try:
            path.unlink()
            # Clean up empty parent directories
            self._cleanup_empty_dirs(path.parent)
        except Exception as e:
            raise IOError(f"Failed to delete file {storage_key}: {str(e)}")

    async def get_url(self, storage_key: str) -> str:
        """
        Get a URL/path to access the stored file.

        For local storage, returns the filesystem path.
        In production, this could return an HTTP URL if files are served
        via a web server.

        Args:
            storage_key: Storage key returned from store().

        Returns:
            Filesystem path (or HTTP URL in production).

        Raises:
            FileNotFoundError: If storage key does not exist.
        """
        path = self.storage_root / storage_key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {storage_key}")

        return str(path)

    def _cleanup_empty_dirs(self, directory: Path) -> None:
        """
        Recursively remove empty parent directories up to storage_root.

        Args:
            directory: Directory to check and potentially remove.
        """
        try:
            # Don't delete storage_root itself
            if directory == self.storage_root:
                return

            # Remove if empty and parent is not storage_root
            if directory.exists() and not any(directory.iterdir()):
                directory.rmdir()
                self._cleanup_empty_dirs(directory.parent)
        except OSError:
            # Directory not empty or other error, stop cleanup
            pass
