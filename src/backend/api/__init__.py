"""API routes package."""

from fastapi import APIRouter

from backend.api.auth import router as auth_router
from backend.api.projects import router as projects_router
from backend.api.models import router as models_router
from backend.api.keys import router as keys_router

__all__ = ["auth_router", "projects_router", "models_router", "keys_router"]
