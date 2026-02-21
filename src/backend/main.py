import asyncio
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status

from backend.api import auth_router, projects_router, models_router, keys_router
from backend.storage import initialize_storage
import backend.storage as storage_module


def require_auth() -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def create_app() -> FastAPI:
    app = FastAPI(title="3D Kenji API", version="0.1.0")

    # Initialize storage backend on startup
    @app.on_event("startup")
    async def startup():
        await initialize_storage(app)

    # Register API routes
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(models_router, prefix="/api/v1")
    app.include_router(keys_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health():
        storage_health = await storage_module._storage_backend.health_check() if storage_module._storage_backend else {"status": "not_initialized"}
        return {
            "status": "ok",
            "components": {
                "storage": storage_health
            }
        }

    @app.get("/api/v1/projects")
    async def list_projects_placeholder():
        return []

    @app.get("/api/v1/models/{model_id}")
    async def get_model_placeholder(model_id: str):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return app

app = create_app()
