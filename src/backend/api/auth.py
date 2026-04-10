"""Authentication API endpoints."""

import os
import logging
import hashlib
from datetime import datetime
from typing import Optional, Callable

from fastapi import APIRouter, HTTPException, status, Depends, Header, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ValidationError, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger(__name__)

from backend.db import get_db
from backend.core.auth import create_access_token, decode_token
from backend.core.validation import (
    LoginRequest as ValidatedLoginRequest,
    RegisterRequest as ValidatedRegisterRequest,
    format_validation_errors,
    sanitize_text_input,
)
from backend.plugins.auth_password import PasswordAuthProvider
from backend.services.user_service import UserService
from backend.models.api_key import APIKey
from backend.api.frontend import templates


router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """User response."""

    id: str
    username: str
    email: str
    display_name: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# Dependency functions
def get_bearer_token(
    request: Request,
    authorization: Optional[str] = Header(None)
) -> str:
    """Extract bearer token from Authorization header or cookie.
    
    Args:
        request: FastAPI Request object
        authorization: Authorization header value
        
    Returns:
        Bearer token
        
    Raises:
        HTTPException: If token is missing or invalid format
    """
    # First try Authorization header
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    # Then try cookie
    token = request.cookies.get("access_token")
    if token:
        return token
    
    # No token found
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authorization required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _get_user_id_from_jwt(db: Session, token: str) -> str:
    """Validate a JWT token and return the user ID."""
    token_payload = decode_token(token)
    auth_provider = PasswordAuthProvider(db)

    user_identity = await auth_provider.validate_token(token)
    if not user_identity:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_payload.user_id


def _get_user_id_from_api_key(
    db: Session,
    token: str,
    required_scopes: Optional[list[str]] = None,
) -> str:
    """Validate an API key and return the owning user ID."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    api_key = db.execute(
        select(APIKey).where(APIKey.key_hash == token_hash, APIKey.revoked.is_(False))
    ).scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if api_key.expires_at and api_key.expires_at <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if required_scopes:
        key_scopes = set(api_key.scopes or [])
        missing_scopes = [scope for scope in required_scopes if scope not in key_scopes]
        if missing_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API key does not have required scope",
            )

    return api_key.owner_id


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_bearer_token),
) -> str:
    """Extract and validate current user from JWT token."""
    try:
        return await _get_user_id_from_jwt(db, token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def require_scopes(required_scopes: Optional[list[str]] = None) -> Callable:
    """Dependency factory that accepts JWTs or API keys with optional scopes."""
    async def _dependency(
        db: Session = Depends(get_db),
        token: str = Depends(get_bearer_token),
    ) -> str:
        if "." in token:
            return await _get_user_id_from_jwt(db, token)

        return _get_user_id_from_api_key(db, token, required_scopes)

    return _dependency


# Endpoint implementations
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request_obj: Request,
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new user.
    
    Args:
        request_obj: FastAPI Request object
        request: Registration request with username, email, display_name, password
        db: Database session
        
    Returns:
        TokenResponse with access token and user info
        
    Raises:
        HTTPException: If username/email already exists or validation fails
    """
    auth_provider = PasswordAuthProvider(db)
    
    # Check if this is the first user (should be admin)
    from sqlalchemy import select, func
    from backend.models.user import User
    user_count = db.execute(select(func.count()).select_from(User)).scalar()
    is_first_user = user_count == 0
    
    # Sanitize display_name to prevent XSS
    try:
        sanitized_display_name = sanitize_text_input(request.display_name, "Display name")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    try:
        user_identity = await auth_provider.create_user(
            username=request.username,
            email=request.email,
            display_name=sanitized_display_name,
            password=request.password,
        )
        
        # Make first user an admin and disable setup mode
        if is_first_user:
            user = db.execute(select(User).where(User.id == user_identity.user_id)).scalar_one()
            user.is_admin = True
            db.commit()
            request_obj.app.state.setup_required = False
            logger.info(f"First user {user.username} created as admin, setup completed")
            
    except ValueError as e:
        error_msg = str(e)
        # Return 409 Conflict for duplicate username/email
        if "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=error_msg,
            )
        # Return 400 Bad Request for other validation errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    # Create JWT token
    token = create_access_token(user_identity.user_id, user_identity.username)

    return TokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=UserResponse(
            id=user_identity.user_id,
            username=user_identity.username,
            email=user_identity.email,
            display_name=user_identity.display_name,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Login with username and password.
    
    Args:
        request: Login request with username and password
        db: Database session
        
    Returns:
        TokenResponse with access token and user info
        
    Raises:
        HTTPException: If credentials are invalid
    """
    auth_provider = PasswordAuthProvider(db)
    
    try:
        auth_result = await auth_provider.authenticate(
            credentials={"username": request.username, "password": request.password}
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create JWT token
    token = create_access_token(auth_result.user_id, auth_result.username)

    return TokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=UserResponse(
            id=auth_result.user_id,
            username=auth_result.username,
            email=auth_result.email,
            display_name=auth_result.display_name,
        ),
    )


@router.post("/password-change", response_model=UserResponse)
async def change_password(
    request: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: str = Depends(get_current_user),
) -> UserResponse:
    """Change password for authenticated user.
    
    Args:
        request: Password change request with current and new password
        db: Database session
        current_user: Current authenticated user ID (from token)
        
    Returns:
        UserResponse with updated user info
        
    Raises:
        HTTPException: If current password is wrong or validation fails
    """
    user_service = UserService(db)
    auth_provider = PasswordAuthProvider(db)
    
    # Verify current password
    try:
        user_dto = user_service.get_user_by_id(current_user)
        if not user_dto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        
        # Verify current password
        verified_user = user_service.verify_password(
            user_dto.username, request.current_password
        )
        if not verified_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect",
            )
        
        # Update password
        updated_identity = await auth_provider.update_password(
            current_user, request.new_password
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return UserResponse(
        id=updated_identity.user_id,
        username=updated_identity.username,
        email=updated_identity.email,
        display_name=updated_identity.display_name,
    )


# Form validation endpoints for HTMX
@router.post("/validate/login")
async def validate_login_form(
    request: Request,
    username_or_email: str = Form(),
    password: str = Form(),
    db: Session = Depends(get_db),
):
    """Validate login form and return errors or success."""
    logger.info(f"Login form submitted: username_or_email={username_or_email}")
    try:
        # Validate inputs
        validated = ValidatedLoginRequest(
            username_or_email=username_or_email,
            password=password,
        )
        
        # If validation passed, resolve email -> username (if needed), then authenticate.
        login_identifier = validated.username_or_email
        user_service = UserService(db)
        if "@" in login_identifier:
            user_by_email = user_service.get_user_by_email(login_identifier)
            if user_by_email:
                login_identifier = user_by_email.username

        # Try to authenticate
        auth_provider = PasswordAuthProvider(db)
        try:
            auth_result = await auth_provider.authenticate(
                credentials={"username": login_identifier, "password": validated.password}
            )
            
            # Create JWT token
            token = create_access_token(auth_result.user_id, auth_result.username)
            
            # Create redirect response with cookie
            response = RedirectResponse(url="/projects", status_code=303)
            response.set_cookie(
                key="access_token",
                value=token.access_token,
                httponly=True,
                max_age=3600 * 24 * 7,  # 7 days
                samesite="lax"
            )
            # HTMX-aware redirect keeps login flow deterministic in XHR mode.
            response.headers["HX-Redirect"] = "/projects"
            return response
            
        except ValueError as e:
            # Invalid credentials
            return templates.TemplateResponse("fragments/error-alert.html", {
                "request": request,
                "message": "Invalid username/email or password",
                "errors": {},
            }, status_code=401)
    
    except ValidationError as e:
        errors = format_validation_errors(e)
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Validation failed",
            "errors": errors,
        }, status_code=400)


@router.post("/validate/register")
async def validate_register_form(
    request: Request,
    username: str = Form(),
    email: str = Form(),
    display_name: str = Form(None),
    password: str = Form(),
    password_confirm: str = Form(),
    db: Session = Depends(get_db),
):
    """Validate registration form and return errors or success."""
    logger.info(f"Register form submitted: username={username}, email={email}")
    try:
        # Validate inputs
        validated = ValidatedRegisterRequest(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
            password_confirm=password_confirm,
        )
        
        # Check if username/email already exists
        user_service = UserService(db)
        if user_service.get_user_by_username(validated.username):
            return templates.TemplateResponse("fragments/error-alert.html", {
                "request": request,
                "message": "Validation failed",
                "errors": {"username": ["Username already exists"]},
            })
        
        if user_service.get_user_by_email(validated.email):
            return templates.TemplateResponse("fragments/error-alert.html", {
                "request": request,
                "message": "Validation failed",
                "errors": {"email": ["Email already registered"]},
            })
        
        # If validation passed, create user
        auth_provider = PasswordAuthProvider(db)
        user_identity = await auth_provider.create_user(
            username=validated.username,
            email=validated.email,
            display_name=validated.display_name or validated.username,
            password=validated.password,
        )
        
        # Create JWT token
        token = create_access_token(user_identity.user_id, user_identity.username)
        
        # Create redirect response with cookie
        response = RedirectResponse(url="/projects", status_code=302)
        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=True,
            max_age=3600 * 24 * 7,  # 7 days
            samesite="lax"
        )
        return response
    
    except ValidationError as e:
        errors = format_validation_errors(e)
        logger.error(f"Validation error in register: {errors}")
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Validation failed",
            "errors": errors,
        })
    except Exception as e:
        logger.error(f"Unexpected error in register: {type(e).__name__}: {str(e)}", exc_info=True)
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": f"Server error: {str(e)}",
            "errors": {},
        })


@router.post("/logout")
async def logout(request: Request):
    """Logout endpoint - clear authentication cookie and redirect to login."""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=None
    )
    logger.info("User logged out successfully")
    return response
