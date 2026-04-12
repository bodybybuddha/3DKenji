"""Project invitation model."""

import uuid

from sqlalchemy import Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class ProjectInvitation(BaseModel):
    """Stores invitation records for project collaboration."""

    __tablename__ = "project_invitations"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    invited_email = Column(String(255), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="viewer")
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    invited_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="invitations")
    invited_by = relationship("User", foreign_keys=[invited_by_id], back_populates="sent_project_invitations")