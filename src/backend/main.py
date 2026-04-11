import asyncio
import os
from datetime import datetime
from time import monotonic
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from backend.api import auth_router, projects_router, models_router, keys_router, health_router, users_router
from backend.api.admin import router as admin_router
from backend.api.frontend import router as frontend_router, create_theme_router
from backend.storage import initialize_storage
from backend.logging_config import logger
from backend.core.plugins import PluginManager
from backend.themes import ThemeManager
from backend.observability import register_sqlalchemy_metrics, record_request_metric
import backend.storage as storage_module
from backend.db import get_session_factory, get_engine
from backend.db.base import Base
from backend.models.user import User


def require_auth() -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


def create_app() -> FastAPI:
    app = FastAPI(title="3D Kenji API", version="1.0.0")
    app.state.setup_required = False
    app.state.start_time = datetime.now()

    # Initialize storage backend on startup
    @app.on_event("startup")
    async def startup():
        logger.info("3D Kenji API starting up")
        app.state.start_time = datetime.now()
        
        # Create database tables if they don't exist
        try:
            engine = get_engine()
            register_sqlalchemy_metrics(engine)
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables initialized")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
        
        await initialize_storage(app)
        logger.info("Storage backend initialized")
        
        # Initialize theme manager
        try:
            plugin_manager = PluginManager()
            # First load all plugins
            await plugin_manager.load_plugins(app, {})
            # Then initialize theme manager with loaded plugins
            app.state.theme_manager = ThemeManager(plugin_manager)
            await app.state.theme_manager.load_themes()
            logger.info("Theme manager initialized")
        except Exception as e:
            logger.error(f"Failed to initialize theme manager: {e}")

        # Determine if initial setup is required
        # Setup is required if NO admins exist (allows multiple admins)
        session = None
        try:
            session = get_session_factory()()
            admin_exists = session.execute(
                select(User).where(User.is_admin.is_(True))
            ).first() is not None
            app.state.setup_required = not admin_exists
        except Exception as e:
            logger.error(f"Failed to determine setup state: {e}")
            app.state.setup_required = False
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass

    @app.middleware("http")
    async def setup_guard(request, call_next):
        request_start = monotonic()
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        response = None

        try:
            if getattr(app.state, "setup_required", False):
                path = request.url.path
                if (
                    path.startswith("/setup")
                    or path.startswith("/static/")
                    or path.startswith("/api/v1/theme/css")
                    or path.startswith("/api/v1/theme/list")
                    or path.startswith("/api/v1/theme/variables")
                    or path.startswith("/api/v1/health")
                    or path.startswith("/api/v1/auth")
                ):
                    response = await call_next(request)
                else:
                    response = RedirectResponse(url="/setup", status_code=303)
            else:
                response = await call_next(request)

            status_code = response.status_code
            return response
        finally:
            duration_ms = (monotonic() - request_start) * 1000.0
            record_request_metric(duration_ms=duration_ms, status_code=status_code)

    # Register API routes
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(projects_router, prefix="/api/v1")
    app.include_router(models_router, prefix="/api/v1")
    app.include_router(keys_router, prefix="/api/v1")
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(admin_router, prefix="/api/v1")
    
    # Register theme routes
    try:
        # Create theme router after app is set up
        def on_startup_theme():
            theme_router = create_theme_router(app.state.theme_manager)
            app.include_router(theme_router)
        
        # Register theme routes if theme manager available
        @app.on_event("startup")
        async def setup_theme_routes():
            if hasattr(app.state, 'theme_manager'):
                theme_router = create_theme_router(app.state.theme_manager)
                app.include_router(theme_router)
    except Exception as e:
        logger.warning(f"Failed to set up theme routes: {e}")
    
    # Register frontend routes
    app.include_router(frontend_router)
    
    logger.info("API routes registered")

    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "..", "frontend", "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
        logger.info(f"Static files mounted from {static_dir}")

    @app.get("/api/v1/projects")
    async def list_projects_placeholder():
        return []

    @app.get("/api/v1/models/{model_id}")
    async def get_model_placeholder(model_id: str):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

    return app

app = create_app()
