from fastapi import Depends, FastAPI, HTTPException, status

from backend.api import auth_router


def require_auth() -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

def create_app() -> FastAPI:
    app = FastAPI(title="3D Kenji API", version="0.1.0")

    # Register auth routes
    app.include_router(auth_router, prefix="/api/v1")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

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
