"""Project model."""

from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class Project(BaseModel):
    """Project model for organizing 3D printing projects."""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, index=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    custom_metadata = Column(JSON, nullable=False, default=dict)  # JSONB for flexible data

    # Relationships
    owner = relationship("User", back_populates="projects")
    models = relationship("Model", back_populates="project", cascade="all, delete-orphan")
