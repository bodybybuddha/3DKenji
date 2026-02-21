"""API routes package."""

from fastapi import APIRouter

from backend.api.auth import router as auth_router

__all__ = ["auth_router"]
