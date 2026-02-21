import asyncio
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status

from backend.api import auth_router
from backend.core.plugin_interfaces import StorageBackend
from backend.core.plugins import PluginManager
from backend.plugins.storage_local import LocalStorageBackend


# Global storage backend reference
_storage_backend: Optional[StorageBackend] = None


def require_auth() -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


async def _initialize_storage(app: FastAPI) -> StorageBackend:
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


def create_app() -> FastAPI:
    app = FastAPI(title="3D Kenji API", version="0.1.0")

    # Initialize storage backend on startup
    @app.on_event("startup")
    async def startup():
        await _initialize_storage(app)

    # Register auth routes
    app.include_router(auth_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health():
        storage_health = await _storage_backend.health_check() if _storage_backend else {"status": "not_initialized"}
        return {
            "status": "ok",
            "components": {
                "storage": storage_health
            }
        }

    @app.post("/api/v1/keys")
    async def create_key(_: None = Depends(require_auth)):
        return {"detail": "unauthorized"}

    @app.post("/api/v1/projects")
    async def create_project(_: None = Depends(require_auth)):
        return {"detail": "unauthorized"}

    @app.post("/api/v1/projects/{project_id}/models")
    async def upload_model(project_id: str, _: None = Depends(require_auth)):
        return {"detail": "unauthorized", "project_id": project_id}

    @app.get("/api/v1/projects")
    async def list_projects():
        return []

    @app.get("/api/v1/models/{model_id}")
    async def get_model(model_id: str):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return app

app = create_app()
