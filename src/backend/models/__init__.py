"""Models package - export all models."""

from backend.models.user import User
from backend.models.project import Project
from backend.models.api_key import APIKey
from backend.models.app_setting import AppSetting

# NOTE: Model (models table) has been removed - table is dropped in migration 004.
# The model_service.py and api/models.py references will be cleaned up in Phase 2.

__all__ = ["User", "Project", "APIKey", "AppSetting"]
