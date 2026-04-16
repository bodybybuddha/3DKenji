"""Application settings model."""

from sqlalchemy import Column, String, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class AppSetting(BaseModel):
    """Database-backed admin-configurable application setting."""

    __tablename__ = "app_settings"

    id = Column(String(36), primary_key=True, index=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value_json = Column(JSON, nullable=False, default=dict)
    updated_by = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    # Relationships
    updated_by_user = relationship("User", foreign_keys=[updated_by])
