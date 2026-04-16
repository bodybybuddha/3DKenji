"""Project collaborator model."""

import uuid

from sqlalchemy import Column, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class ProjectCollaborator(BaseModel):
    """Maps a user to a project role."""

    __tablename__ = "project_collaborators"

    id = Column(String(36), primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, default="viewer")
    granted_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_collaborator_project_user"),
    )

    project = relationship("Project", back_populates="collaborators")
    user = relationship("User", foreign_keys=[user_id], back_populates="project_collaborations")
    granted_by = relationship("User", foreign_keys=[granted_by_id])