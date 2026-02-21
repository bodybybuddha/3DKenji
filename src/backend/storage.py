"""Storage backend initialization and dependency injection."""

from typing import Optional

from backend.core.plugin_interfaces import StorageBackend
from backend.plugins.storage_local import LocalStorageBackend
from fastapi import FastAPI

# Global storage backend reference
_storage_backend: Optional[StorageBackend] = None


async def initialize_storage(app: FastAPI) -> StorageBackend:
    """Initialize storage backend on app startup."""
    global _storage_backend
    
    # For MVP, use local filesystem storage
    # In future, could load from config: os.getenv("STORAGE_BACKEND", "local")
    storage = LocalStorageBackend()
    await storage.register(app, config=None)
    
    # Run health check
    health = await storage.health_check()
    if health["status"] != "healthy":
        raise RuntimeError(f"Storage backend failed health check: {health}")
    
    _storage_backend = storage
    return storage


def get_storage() -> StorageBackend:
    """Dependency: get the configured storage backend."""
    if _storage_backend is None:
        raise RuntimeError("Storage backend not initialized")
    return _storage_backend
