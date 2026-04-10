"""Project model."""

from sqlalchemy import Column, String, Boolean, BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class Project(BaseModel):
    """Project model for organizing 3D printing projects."""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, index=True)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)

    # Directory-based storage fields
    slug = Column(String(64), nullable=False)
    category = Column(String(255), nullable=False, default="Uncategorized")
    directory_path = Column(String(1024), nullable=True)
    disk_size_bytes = Column(BigInteger, nullable=True, default=0)
    is_archived = Column(Boolean, nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint("owner_id", "category", "slug", name="uq_project_owner_category_slug"),
    )

    # Relationships
    owner = relationship("User", back_populates="projects")
