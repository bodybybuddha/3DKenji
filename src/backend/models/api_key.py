"""API Key model."""

from sqlalchemy import Column, String, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.base import BaseModel


class APIKey(BaseModel):
    """API key for programmatic access (scoped)."""

    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, index=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Human-readable name for the key
    key_identifier = Column(String(64), unique=True, nullable=False, index=True)  # Prefix for lookup
    key_hash = Column(String(255), nullable=False)  # bcrypt hash of full key
    scopes = Column(JSON, nullable=False, default=list)  # e.g., ["project:read", "model:write"]
    expires_at = Column(DateTime, nullable=True)  # None = never expires
    revoked = Column(Boolean, default=False, nullable=False, index=True)
    description = Column(String(255), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="api_keys")
