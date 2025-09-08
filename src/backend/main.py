from fastapi import FastAPI

def create_app() -> FastAPI:
    app = FastAPI(title="3D Kenji API", version="0.1.0")

    @app.get("/api/v1/health")
    async def health():
        return {"status": "ok"}

    return app

app = create_app()
