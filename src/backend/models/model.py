"""Model (3D file) model."""

from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class Model(BaseModel):
    """3D model file record."""

    __tablename__ = "models"

    id = Column(String(36), primary_key=True, index=True)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False, index=True)
    uploaded_by_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    source_url = Column(Text, nullable=True)  # Where model came from
    tags = Column(JSON, nullable=False, default=list)  # List of tag strings
    custom_metadata = Column(JSON, nullable=False, default=dict)  # JSONB for flexible data
    storage_key = Column(String(255), nullable=False, index=True)  # Storage backend identifier

    # Relationships (table being dropped in migration 004 – remove back_populates)
    project = relationship("Project")
    uploaded_by_user = relationship("User")
