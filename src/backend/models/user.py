"""User model."""

import uuid

from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class User(BaseModel):
    """User account model."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    nickname = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        default=lambda: f"user-{uuid.uuid4().hex[:12]}",
    )
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)  # Hashed password for local auth
    is_admin = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="owner")
    project_collaborations = relationship(
        "ProjectCollaborator",
        foreign_keys="ProjectCollaborator.user_id",
        back_populates="user",
    )
    sent_project_invitations = relationship(
        "ProjectInvitation",
        foreign_keys="ProjectInvitation.invited_by_id",
        back_populates="invited_by",
    )
