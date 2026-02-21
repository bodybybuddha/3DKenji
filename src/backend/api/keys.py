"""API Keys management endpoints."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import secrets
import hashlib

from backend.api.auth import get_current_user
from backend.db import get_db
from backend.models.api_key import APIKey
from backend.services.user_service import UserService
from sqlalchemy import select

# Initialize templates for HTML responses
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="/keys", tags=["api-keys"])


# Request Models
class CreateAPIKeyRequest(BaseModel):
    """Request to create an API key."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-friendly name for the key")
    scopes: list[str] = Field(default=["read"], description="Permission scopes for the key")
    project_ids: Optional[list[str]] = Field(None, description="Limit key to specific projects (optional)")


# Response Models
class APIKeyResponse(BaseModel):
    """API Key response (for creation only, doesn't expose secret)."""

    id: str
    name: str
    key_identifier: str  # Prefix, safe to show
    scopes: list[str]
    project_ids: Optional[list[str]]
    created_at: str
    expires_at: Optional[str]

    class Config:
        from_attributes = True


class APIKeyWithSecretResponse(APIKeyResponse):
    """API Key with secret (only shown at creation time)."""

    secret: str


class APIKeyListResponse(BaseModel):
    """List of API keys (without secrets)."""

    items: list[APIKeyResponse]
    total: int


def _generate_key_pair() -> tuple[str, str, str]:
    """
    Generate API key pair (identifier + secret).

    Returns:
        Tuple of (key_identifier, hashed_secret, plaintext_secret)
    """
    # Generate a random secret key (32 bytes)
    secret = secrets.token_urlsafe(32)
    
    # Create identifier prefix (first 7 chars of secret)
    identifier = f"3dkenji_{secret[:7]}"
    
    # Hash secret for storage
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    
    return identifier, secret_hash, secret


@router.post("", status_code=status.HTTP_201_CREATED, response_model=APIKeyWithSecretResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> APIKeyWithSecretResponse:
    """
    Create a new API key.

    API keys are long-lived tokens that can be used for programmatic access.
    The secret is only shown at creation time; it cannot be retrieved later.

    Args:
        request: CreateAPIKeyRequest with name and scopes.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        APIKeyWithSecretResponse with key details and secret (201 Created).
        **IMPORTANT**: Save the secret immediately, it will not be shown again.

    Raises:
        400: If request is invalid.
        401: If user is not authenticated.
    """
    import uuid
    from datetime import datetime, timedelta

    try:
        identifier, secret_hash, secret = _generate_key_pair()

        # Create API key record
        api_key = APIKey(
            id=str(uuid.uuid4()),
            owner_id=current_user_id,
            name=request.name,
            key_identifier=identifier,
            hashed_key=secret_hash,
            scopes=request.scopes,
            project_ids=request.project_ids or [],
            # Keys expire in 1 year by default (can be made configurable)
            expires_at=datetime.utcnow() + timedelta(days=365),
        )

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        # Build response with the plaintext secret (only shown once)
        return APIKeyWithSecretResponse(
            id=api_key.id,  # type: ignore[arg-type]
            name=api_key.name,  # type: ignore[arg-type]
            key_identifier=api_key.key_identifier,  # type: ignore[arg-type]
            scopes=api_key.scopes,  # type: ignore[arg-type]
            project_ids=api_key.project_ids,  # type: ignore[arg-type]
            created_at=api_key.created_at.isoformat(),  # type: ignore[arg-type]
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,  # type: ignore[arg-type]
            secret=secret,  # This is the only time it's returned!
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}",
        )


@router.get("", response_model=APIKeyListResponse)
async def list_api_keys(
    format: Optional[str] = None,
    request: Request = None,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> APIKeyListResponse:
    """
    List all API keys for the authenticated user.

    Secrets are NOT returned in this list for security reasons.
    HTML format supported via ?format=html for HTMX integration.

    Args:
        format: Response format ('html' for HTMX, default returns JSON).
        request: FastAPI Request object (injected).
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        APIKeyListResponse with list of keys (200 OK).
        If format=html, returns HTML snippet instead.

    Raises:
        401: If user is not authenticated.
    """
    keys = session.execute(
        select(APIKey).where(APIKey.owner_id == current_user_id)
    ).scalars().all()

    # Return HTML fragment for HTMX
    if format == "html":
        return HTMLResponse(
            templates.get_template("fragments/keys-list.html").render(
                request=request,
                keys=[{
                    "id": k.id,
                    "name": k.name,
                    "key_prefix": k.key_identifier[:20],
                    "scopes": k.scopes,
                    "last_used_at": getattr(k, "last_used_at", None),
                    "expires_at": k.expires_at.isoformat() if k.expires_at else None,
                } for k in keys],
            )
        )

    return APIKeyListResponse(
        items=[
            APIKeyResponse(
                id=k.id,  # type: ignore[arg-type]
                name=k.name,  # type: ignore[arg-type]
                key_identifier=k.key_identifier,  # type: ignore[arg-type]
                scopes=k.scopes,  # type: ignore[arg-type]
                project_ids=k.project_ids,  # type: ignore[arg-type]
                created_at=k.created_at.isoformat(),  # type: ignore[arg-type]
                expires_at=k.expires_at.isoformat() if k.expires_at else None,  # type: ignore[arg-type]
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    """
    Revoke (delete) an API key.

    The key will no longer work for authentication. This is irreversible.

    Args:
        key_id: ID of API key to revoke.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        Empty response (204 No Content).

    Raises:
        401: If user is not authenticated.
        403: If user does not own the API key.
        404: If API key not found.
    """
    key = session.execute(
        select(APIKey).where(APIKey.id == key_id)
    ).scalar_one_or_none()

    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key '{key_id}' not found",
        )

    # Check ownership
    if key.owner_id != current_user_id:  # type: ignore[comparison-overlap]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to revoke this API key",
        )

    try:
        session.delete(key)
        session.commit()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}",
        )

# Modal endpoints for HTMX form loading
@router.get("/create-modal", response_class=HTMLResponse)
async def get_create_key_modal(
    request: Request,
    current_user_id: str = Depends(get_current_user),
) -> str:
    """Get the create API key modal form."""
    return templates.TemplateResponse("keys/form-modal.html", {
        "request": request,
    }).body.decode()