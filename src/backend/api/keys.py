"""API Keys management endpoints."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError, validator
from sqlalchemy.orm import Session
import secrets
import hashlib

from backend.api.auth import get_current_user
from backend.db import get_db
from backend.models.api_key import APIKey
from backend.core.validation import sanitize_text_input, VALID_SCOPES
from backend.api.frontend import templates
from sqlalchemy import select

router = APIRouter(prefix="/keys", tags=["api-keys"])


# Request Models
class CreateAPIKeyRequest(BaseModel):
    """Request to create an API key via the JSON API."""

    name: str = Field(..., min_length=1, max_length=255, description="Human-friendly name for the key")
    scopes: list[str] = Field(default=["read:projects"], description="Permission scopes for the key")
    expires_at: Optional[str] = Field(None, description="ISO 8601 date/datetime for key expiration; omit or null for no expiration")

    @validator("scopes")
    def validate_scopes(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one scope must be selected")
        for scope in v:
            if scope not in VALID_SCOPES:
                raise ValueError(f"Invalid scope: {scope!r}. Allowed: {', '.join(VALID_SCOPES)}")
        return v


# Response Models
class APIKeyResponse(BaseModel):
    """API Key response (for creation only, doesn't expose secret)."""

    id: str
    name: str
    key_identifier: str  # Prefix, safe to show
    scopes: list[str]
    created_at: str
    expires_at: Optional[str]

    class Config:
        from_attributes = True


class APIKeyWithSecretResponse(APIKeyResponse):
    """API Key with secret (only shown at creation time)."""

    key: str
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
    req: Request,
    name: Optional[str] = Form(None),
    scopes: Optional[list[str]] = Form(None),
    expiry_days: Optional[int] = Form(None),
    expire_on: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> APIKeyWithSecretResponse:
    """
    Create a new API key.

    API keys are long-lived tokens that can be used for programmatic access.
    The secret is only shown at creation time; it cannot be retrieved later.

    Expiration rules:
    - JSON: ``expires_at`` ISO 8601 string → use that date; ``null`` or omitted → no expiration.
    - Form: ``expire_on`` date string → use that date; ``expiry_days`` integer → offset from today;
      both absent or empty → no expiration.

    Raises:
        400: If request is invalid.
        401: If user is not authenticated.
    """
    import uuid
    from datetime import datetime, timedelta, timezone

    try:
        content_type = req.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await req.json()
            request = CreateAPIKeyRequest(**body)

            # Determine expiry from JSON expires_at (null / omitted → never)
            expires_at_dt = None
            if request.expires_at:
                try:
                    expires_at_dt = datetime.fromisoformat(
                        request.expires_at.replace("Z", "+00:00")
                    ).replace(tzinfo=None)  # store naive UTC
                    if expires_at_dt <= datetime.utcnow():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="expires_at must be in the future",
                        )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid expires_at format. Expected ISO 8601: {exc}",
                    )
        else:
            # Form path: validate via shared validator then compute expiry independently.
            from backend.core.validation import CreateAPIKeyRequest as ValidatedKeyRequest

            validated = ValidatedKeyRequest(
                name=name or "",
                scopes=scopes or ["read:projects"],
                expiry_days=expiry_days,
            )
            request = CreateAPIKeyRequest(
                name=validated.name,
                scopes=validated.scopes,
                expires_at=None,
            )

            expires_at_dt = None
            if expire_on and expire_on.strip():
                try:
                    expires_at_dt = datetime.strptime(expire_on.strip(), "%Y-%m-%d")
                    if expires_at_dt.date() <= datetime.utcnow().date():
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Expiration date must be in the future",
                        )
                except ValueError as exc:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Invalid expiration date format (expected YYYY-MM-DD): {exc}",
                    )
            elif expiry_days:
                expires_at_dt = datetime.utcnow() + timedelta(days=expiry_days)
            # else: expires_at_dt stays None → never expires

        # Sanitize name
        if request.name.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="name cannot be empty or whitespace only",
            )
        try:
            sanitized_name = sanitize_text_input(request.name.strip(), "API key name")
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

        identifier, secret_hash, secret = _generate_key_pair()

        api_key = APIKey(
            id=str(uuid.uuid4()),
            owner_id=current_user_id,
            name=sanitized_name,
            key_identifier=identifier,
            key_hash=secret_hash,
            scopes=request.scopes,
            expires_at=expires_at_dt,
        )

        session.add(api_key)
        session.commit()
        session.refresh(api_key)

        return APIKeyWithSecretResponse(
            id=api_key.id,  # type: ignore[arg-type]
            name=api_key.name,  # type: ignore[arg-type]
            key_identifier=api_key.key_identifier,  # type: ignore[arg-type]
            scopes=api_key.scopes,  # type: ignore[arg-type]
            created_at=api_key.created_at.isoformat(),  # type: ignore[arg-type]
            expires_at=api_key.expires_at.isoformat() if api_key.expires_at else None,  # type: ignore[arg-type]
            key=secret,
            secret=secret,  # Only shown at creation time — save it!
        )

    except HTTPException:
        raise
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=exc.errors(),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(exc)}",
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
                created_at=k.created_at.isoformat(),  # type: ignore[arg-type]
                expires_at=k.expires_at.isoformat() if k.expires_at else None,  # type: ignore[arg-type]
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    request: Request,
    key_id: str,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> Response:
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

        if request.headers.get("HX-Request") == "true":
            return HTMLResponse(content="", status_code=200)

        return Response(status_code=status.HTTP_204_NO_CONTENT)
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
    from datetime import date
    return templates.TemplateResponse("keys/form-modal.html", {
        "request": request,
        "today": date.today().isoformat(),
    }).body.decode()

# Form validation endpoints
@router.post("/validate/create", response_class=HTMLResponse)
async def validate_create_key(
    request: Request,
    name: str = None,
    scopes: list[str] = None,
    expiry_days: int = None,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Validate API key creation form."""
    try:
        from backend.core.validation import CreateAPIKeyRequest as ValidatedKeyRequest, format_validation_errors
        
        # Validate inputs
        ValidatedKeyRequest(
            name=name or "",
            scopes=scopes or ["read:models"],
            expiry_days=expiry_days,
        )
        
        # Create API key would happen here
        return JSONResponse({
            "success": True,
            "message": "API key created successfully",
            "key_id": "key_123",
        })
    
    except ValidationError as e:
        from backend.core.validation import format_validation_errors
        errors = format_validation_errors(e)
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Validation failed",
            "errors": errors,
        }, status_code=400)
    except Exception as e:
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Failed to create API key",
            "errors": {"general": [str(e)]},
        }, status_code=500)
