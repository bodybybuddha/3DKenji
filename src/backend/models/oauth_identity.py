"""OAuth/OIDC identity model for provider-linked accounts."""

from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.db.base import BaseModel


class OAuthIdentity(BaseModel):
    """OAuth/OIDC identity linking a user to an external provider."""

    __tablename__ = "oauth_identities"

    id = Column(String(36), primary_key=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(64), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False)
    provider_email = Column(String(255), nullable=True)
    provider_display_name = Column(String(255), nullable=True)
    linked_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="oauth_identities")

    # Table constraints
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_identity_provider_sub"),
        Index("ix_oauth_identities_provider_user_id", "provider", "provider_user_id"),
    )
