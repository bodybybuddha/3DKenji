import asyncio
import os
from datetime import datetime
from time import monotonic
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

from backend.api import auth_router, projects_router, models_router, keys_router, health_router, users_router
from backend.api.admin import router as admin_router
from backend.api.frontend import router as frontend_router, create_theme_router
from backend.storage import initialize_storage
from backend.logging_config import logger, configure_logging
from backend.core.plugins import PluginManager, get_plugins_root
from backend.core.auth import JWT_SECRET, JWT_ALGORITHM
from backend.themes import ThemeManager
from backend.observability import register_sqlalchemy_metrics, record_request_metric
import backend.storage as storage_module
from backend.db import get_session_factory, get_engine
from backend.db.base import Base
from backend.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_jwt_identity(request: Request) -> tuple[Optional[str], Optional[str]]:
    """Best-effort extraction of (user_id, username) from the request JWT.

    Reads the access_token cookie or the Authorization header.  Never raises.
    """
    token: Optional[str] = None
    try:
        token = request.cookies.get("access_token")
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
        if not token:
            return None, None
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("user_id"), payload.get("username")
    except Exception:
        return None, None


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

        # Load persisted log settings from database and apply to live logger
        try:
            from backend.services.app_settings_service import AppSettingsService
            _log_sess = get_session_factory()()
            try:
                log_settings = AppSettingsService(_log_sess).get_log_settings()
                configure_logging(
                    log_level=log_settings["log_level"],
                    max_size_mb=log_settings["max_size_mb"],
                    backup_count=log_settings["backup_count"],
                )
                logger.info(
                    "Log settings applied from DB",
                    extra={
                        "detail": (
                            f"level={log_settings['log_level']} "
                            f"max_size_mb={log_settings['max_size_mb']} "
                            f"backup_count={log_settings['backup_count']}"
                        )
                    },
                )
            finally:
                _log_sess.close()
        except Exception as _log_exc:
            logger.warning("Could not load log settings from DB: %s", _log_exc)

        await initialize_storage(app)
        logger.info("Storage backend initialized")
        
        # Initialize theme manager
        try:
            plugin_manager = PluginManager(get_plugins_root())
            # First load all plugins
            await plugin_manager.load_plugins(app, {})
            app.state.plugin_manager = plugin_manager
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

    # ---------------------------------------------------------------------------
    # Access logging middleware — logs every HTTP request to the app logger.
    # Health-check polling is excluded to prevent log noise.
    # ---------------------------------------------------------------------------
    _ACCESS_LOG_SKIP_PREFIX = "/api/v1/health"

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        start = monotonic()
        user_id, username = _extract_jwt_identity(request)
        client_ip = (request.client.host if request.client else "unknown")
        response = None
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception:
            raise
        finally:
            if not request.url.path.startswith(_ACCESS_LOG_SKIP_PREFIX):
                duration_ms = round((monotonic() - start) * 1000.0, 2)
                logger.info(
                    "HTTP %s %s %d",
                    request.method,
                    request.url.path,
                    status_code,
                    extra={
                        "event": "http_request",
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "client_ip": client_ip,
                        "user_id": user_id,
                        "username": username,
                    },
                )

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

    # ---------------------------------------------------------------------------
    # Global exception handler — ensures unhandled errors reach the file logger.
    # ---------------------------------------------------------------------------
    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        user_id, username = _extract_jwt_identity(request)
        logger.error(
            "Unhandled exception: %s %s — %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
            exc,
            exc_info=True,
            extra={
                "event": "unhandled_exception",
                "method": request.method,
                "path": request.url.path,
                "user_id": user_id,
                "username": username,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again later."},
        )

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
