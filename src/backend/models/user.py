"""User model."""

from sqlalchemy import Column, String, Text, Boolean
from sqlalchemy.orm import relationship

from backend.db.base import BaseModel


class User(BaseModel):
    """User account model."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    password_hash = Column(Text, nullable=False)  # Hashed password for local auth
    is_admin = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    # Relationships
    projects = relationship("Project", back_populates="owner")
    api_keys = relationship("APIKey", back_populates="owner")
