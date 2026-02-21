"""Authentication API endpoints."""

import os
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Header, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError, EmailStr, Field
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.core.auth import create_access_token, decode_token
from backend.core.validation import (
    LoginRequest as ValidatedLoginRequest,
    RegisterRequest as ValidatedRegisterRequest,
    format_validation_errors,
)
from backend.plugins.auth_password import PasswordAuthProvider
from backend.services.user_service import UserService

# Initialize templates for HTML responses
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=8)


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
def get_bearer_token(authorization: Optional[str] = Header(None)) -> str:
    """Extract bearer token from Authorization header.
    
    Args:
        authorization: Authorization header value
        
    Returns:
        Bearer token
        
    Raises:
        HTTPException: If token is missing or invalid format
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return parts[1]


async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(get_bearer_token),
) -> str:
    """Extract and validate current user from JWT token.
    
    Args:
        db: Database session
        token: Bearer token from header
        
    Returns:
        User ID
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        token_payload = decode_token(token)
        auth_provider = PasswordAuthProvider(db)
        
        # Validate token and ensure user still exists
        user_identity = await auth_provider.validate_token(token)
        if not user_identity:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return token_payload.user_id
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# Endpoint implementations
@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new user.
    
    Args:
        request: Registration request with username, email, display_name, password
        db: Database session
        
    Returns:
        TokenResponse with access token and user info
        
    Raises:
        HTTPException: If username/email already exists or validation fails
    """
    auth_provider = PasswordAuthProvider(db)
    
    try:
        user_identity = await auth_provider.create_user(
            username=request.username,
            email=request.email,
            display_name=request.display_name,
            password=request.password,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
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
@router.post("/validate/login", response_class=HTMLResponse)
async def validate_login_form(
    request: Request,
    username_or_email: str = None,
    password: str = None,
    db: Session = Depends(get_db),
):
    """Validate login form and return errors or success."""
    try:
        # Validate inputs
        validated = ValidatedLoginRequest(
            username_or_email=username_or_email or "",
            password=password or "",
        )
        
        # If validation passed, try to authenticate
        auth_provider = PasswordAuthProvider(db)
        try:
            auth_result = await auth_provider.authenticate(
                credentials={"username": validated.username_or_email, "password": validated.password}
            )
            
            # Create JWT token
            token = create_access_token(auth_result.user_id, auth_result.username)
            
            return JSONResponse({
                "success": True,
                "redirect": "/projects",
                "token": token.access_token,
            })
        except ValueError:
            # Invalid credentials
            return templates.TemplateResponse("fragments/error-alert.html", {
                "request": request,
                "message": "Invalid username/email or password",
                "errors": {},
            })
    
    except ValidationError as e:
        errors = format_validation_errors(e)
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Validation failed",
            "errors": errors,
        })


@router.post("/validate/register", response_class=HTMLResponse)
async def validate_register_form(
    request: Request,
    username: str = None,
    email: str = None,
    display_name: str = None,
    password: str = None,
    password_confirm: str = None,
    db: Session = Depends(get_db),
):
    """Validate registration form and return errors or success."""
    try:
        # Validate inputs
        validated = ValidatedRegisterRequest(
            username=username or "",
            email=email or "",
            display_name=display_name,
            password=password or "",
            password_confirm=password_confirm or "",
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
        
        return JSONResponse({
            "success": True,
            "redirect": "/projects",
            "token": token.access_token,
        })
    
    except ValidationError as e:
        errors = format_validation_errors(e)
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Validation failed",
            "errors": errors,
        })
