"""Authentication API endpoints."""

import os
import logging
import hashlib
import secrets
from datetime import datetime
from typing import Optional, Callable

from fastapi import APIRouter, HTTPException, status, Depends, Header, Request, Form, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, ValidationError, EmailStr, Field
from sqlalchemy.orm import Session
from sqlalchemy import select

logger = logging.getLogger(__name__)

from backend.db import get_db
from backend.core.auth import create_access_token, decode_token
from backend.core import oauth_state
from backend.core.validation import (
    LoginRequest as ValidatedLoginRequest,
    RegisterRequest as ValidatedRegisterRequest,
    format_validation_errors,
    sanitize_text_input,
)
from backend.plugins.auth_password import PasswordAuthProvider
from backend.services.app_settings_service import AppSettingsService
from backend.services.user_service import UserService
from backend.services import oauth_service
from backend.models.api_key import APIKey
from backend.models.oauth_identity import OAuthIdentity
from backend.api.frontend import templates


router = APIRouter(prefix="/auth", tags=["auth"])


# Request/Response Models
class RegisterRequest(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=255)
    nickname: Optional[str] = Field(None, min_length=3, max_length=64)
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


class SetLocalPasswordRequest(BaseModel):
    """Request to set local password for OIDC-only admin."""

    new_password: str = Field(..., min_length=8, max_length=128)


class OAuthLinkResponse(BaseModel):
    """OAuth link response with authorization URL."""

    authorize_url: str


class UserResponse(BaseModel):
    """User response."""

    id: str
    username: str
    nickname: str
    email: str
    display_name: str


class TokenResponse(BaseModel):
    """Token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


def _get_oauth_settings(db: Session) -> dict[str, object]:
    return AppSettingsService(db).get_runtime_oauth_settings()


def _require_oauth_provider(settings: dict[str, object], provider: str) -> None:
    if not settings.get("enabled"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth is not enabled",
        )

    if provider != settings.get("provider_name"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown OAuth provider: {provider}",
        )


def _require_oauth_runtime_config(settings: dict[str, object]) -> None:
    if not all([
        settings.get("issuer_url"),
        settings.get("client_id"),
        settings.get("client_secret"),
        settings.get("callback_url"),
    ]):
        logger.error("OIDC configuration incomplete")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth configuration incomplete",
        )


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

    # Record last use — best-effort, never block authentication on failure
    try:
        api_key.last_used_at = datetime.utcnow()  # type: ignore[assignment]
        db.commit()
    except Exception:
        db.rollback()

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
            nickname=request.nickname,
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
            nickname=user_identity.nickname,
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
            nickname=auth_result.nickname,
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
        nickname=updated_identity.nickname,
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
            
            # HTMX requests should use HX-Redirect; non-HTMX callers expect HTTP redirect semantics.
            is_htmx = request.headers.get("HX-Request") == "true"
            response = Response(status_code=204) if is_htmx else RedirectResponse(url="/projects", status_code=303)
            response.set_cookie(
                key="access_token",
                value=token.access_token,
                httponly=True,
                max_age=3600 * 24 * 7,  # 7 days
                samesite="lax"
            )
            if is_htmx:
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
    nickname: str = Form(None),
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
            nickname=nickname,
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
            nickname=validated.nickname,
            email=validated.email,
            display_name=validated.display_name or validated.username,
            password=validated.password,
        )
        
        # Create JWT token
        token = create_access_token(user_identity.user_id, user_identity.username)
        
        # HTMX requests should use HX-Redirect; non-HTMX callers expect HTTP redirect semantics.
        is_htmx = request.headers.get("HX-Request") == "true"
        response = Response(status_code=204) if is_htmx else RedirectResponse(url="/projects", status_code=303)
        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=True,
            max_age=3600 * 24 * 7,  # 7 days
            samesite="lax"
        )
        if is_htmx:
            response.headers["HX-Redirect"] = "/projects"
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


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
) -> UserResponse:
    """Get current authenticated user information.
    
    Args:
        db: Database session
        current_user_id: Current user ID from token
        
    Returns:
        UserResponse with user info
    """
    user_service = UserService(db)
    user_dto = user_service.get_user_by_id(current_user_id)
    
    if not user_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse(
        id=user_dto.id,
        username=user_dto.username,
        nickname=user_dto.nickname,
        email=user_dto.email,
        display_name=user_dto.display_name,
    )


# ===== OAuth/OIDC Routes =====

@router.get("/oauth/{provider}/authorize")
async def oauth_authorize(
    provider: str,
    db: Session = Depends(get_db),
    next_url: Optional[str] = Query(None, alias="next"),
) -> RedirectResponse:
    """Initiate OAuth authorization flow.
    
    Args:
        provider: OAuth provider name
        db: Database session
        next_url: Optional redirect URL after successful login
        
    Returns:
        Redirect to OAuth provider authorization endpoint
    """
    settings = _get_oauth_settings(db)
    _require_oauth_provider(settings, provider)
    _require_oauth_runtime_config(settings)
    
    try:
        # Fetch OIDC discovery config
        discovery_config = oauth_service.get_oidc_discovery_config(
            str(settings["issuer_url"])
        )
        
        # Generate PKCE pair
        code_verifier, code_challenge = oauth_service.generate_pkce_pair()
        
        # Generate state
        state = secrets.token_urlsafe(32)
        
        # Store state and verifier
        oauth_state.store_state(state, code_verifier)
        
        # Build authorization URL
        auth_url = oauth_service.build_authorization_url(
            discover_config=discovery_config,
            state=state,
            code_challenge=code_challenge,
            client_id=str(settings["client_id"]),
            callback_url=str(settings["callback_url"]),
            scopes=str(settings["scopes"]),
        )
        
        return RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        logger.error(f"OAuth authorize error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth flow",
        )


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    """OAuth callback endpoint.
    
    Args:
        provider: OAuth provider name
        code: Authorization code from provider
        state: State parameter from provider
        db: Database session
        
    Returns:
        Response with JWT token cookie and user info
    """
    settings = _get_oauth_settings(db)
    _require_oauth_provider(settings, provider)
    _require_oauth_runtime_config(settings)
    
    # Validate inputs
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing code or state parameter",
        )
    
    try:
        # Consume state and get verifier
        code_verifier, link_user_id = oauth_state.consume_state(state)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired state",
        )
    
    try:
        # Fetch OIDC discovery config
        discovery_config = oauth_service.get_oidc_discovery_config(
            str(settings["issuer_url"])
        )
        
        # Exchange code for tokens
        token_response = oauth_service.exchange_code_for_tokens(
            discover_config=discovery_config,
            code=code,
            code_verifier=code_verifier,
            client_id=str(settings["client_id"]),
            client_secret=str(settings["client_secret"]),
            callback_url=str(settings["callback_url"]),
        )
        
        # Extract and validate ID token
        id_token = token_response.get("id_token")
        if not id_token:
            raise ValueError("No ID token in response")
        
        claims = oauth_service.extract_id_token_claims(
            id_token=id_token,
            client_id=str(settings["client_id"]),
            issuer_url=str(settings["issuer_url"]),
            jwks_uri=discovery_config["jwks_uri"],
        )
        
        # Handle linking flow if link_user_id is present
        if link_user_id:
            # Link to existing user
            user = db.execute(
                select(User).where(User.id == link_user_id)
            ).scalar_one_or_none()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User not found for linking",
                )
            
            # Check if identity already linked
            sub = claims.get("sub")
            existing = db.execute(
                select(OAuthIdentity).where(
                    OAuthIdentity.provider == provider,
                    OAuthIdentity.provider_user_id == sub,
                )
            ).scalar_one_or_none()
            
            if existing:
                if existing.user_id != link_user_id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="OAuth identity already linked to another user",
                    )
            else:
                # Create new identity link
                from backend.models.user import User
                import uuid
                identity = OAuthIdentity(
                    id=str(uuid.uuid4()),
                    user_id=link_user_id,
                    provider=provider,
                    provider_user_id=sub,
                    provider_email=claims.get("email"),
                    provider_display_name=claims.get("name") or claims.get("preferred_username"),
                )
                db.add(identity)
                db.commit()
        else:
            # Normal login/registration flow
            from backend.models.user import User
            user, is_new_user = oauth_service.find_or_create_user_from_claims(
                db=db,
                provider=provider,
                claims=claims,
            )
            
            if is_new_user:
                logger.info(f"New user created via OAuth: {user.username}")  # type: ignore
        
        # Create JWT token
        token = create_access_token(user.id, user.username)  # type: ignore
        
        # Build response
        user_service = UserService(db)
        user_dto = user_service.get_user_by_id(user.id)  # type: ignore
        
        token_response_data = TokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=UserResponse(
                id=user_dto.id,  # type: ignore
                username=user_dto.username,  # type: ignore
                nickname=user_dto.nickname,  # type: ignore
                email=user_dto.email,  # type: ignore
                display_name=user_dto.display_name,  # type: ignore
            ),
        )
        
        # Set cookie and return JSON
        response = JSONResponse(content=token_response_data.dict())
        response.set_cookie(
            key="access_token",
            value=token.access_token,
            httponly=True,
            max_age=token.expires_in,
            samesite="lax",
            secure=bool(settings["cookie_secure"]),
        )
        
        return response
        
    except ValueError as e:
        logger.error(f"OAuth callback validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed",
        )
    except Exception as e:
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication failed",
        )


@router.post("/oauth/{provider}/link", response_model=OAuthLinkResponse)
async def oauth_link(
    provider: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
) -> OAuthLinkResponse:
    """Initiate OAuth linking for currently authenticated user.
    
    Args:
        provider: OAuth provider name
        db: Database session
        current_user_id: Current authenticated user ID
        
    Returns:
        OAuthLinkResponse with authorization URL
    """
    settings = _get_oauth_settings(db)
    _require_oauth_provider(settings, provider)
    _require_oauth_runtime_config(settings)
    
    # Check if already linked
    existing = db.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.user_id == current_user_id,
            OAuthIdentity.provider == provider,
        )
    ).scalar_one_or_none()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="OAuth provider already linked",
        )
    
    try:
        # Fetch OIDC discovery config
        discovery_config = oauth_service.get_oidc_discovery_config(
            str(settings["issuer_url"])
        )
        
        # Generate PKCE pair
        code_verifier, code_challenge = oauth_service.generate_pkce_pair()
        
        # Generate state
        state = secrets.token_urlsafe(32)
        
        # Store state with link_user_id
        oauth_state.store_state(state, code_verifier, link_user_id=current_user_id)
        
        # Build authorization URL
        auth_url = oauth_service.build_authorization_url(
            discover_config=discovery_config,
            state=state,
            code_challenge=code_challenge,
            client_id=str(settings["client_id"]),
            callback_url=str(settings["callback_url"]),
            scopes=str(settings["scopes"]),
        )
        
        return OAuthLinkResponse(authorize_url=auth_url)
        
    except Exception as e:
        logger.error(f"OAuth link error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate OAuth linking",
        )


@router.delete("/oauth/{provider}/unlink", status_code=status.HTTP_204_NO_CONTENT)
async def oauth_unlink(
    provider: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
) -> Response:
    """Unlink OAuth provider from current user.
    
    Args:
        provider: OAuth provider name
        db: Database session
        current_user_id: Current authenticated user ID
        
    Returns:
        204 No Content on success
    """
    # Find OAuth identity
    identity = db.execute(
        select(OAuthIdentity).where(
            OAuthIdentity.user_id == current_user_id,
            OAuthIdentity.provider == provider,
        )
    ).scalar_one_or_none()
    
    if not identity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="OAuth provider not linked",
        )
    
    # Safety check: ensure user has local password before unlinking
    from backend.models.user import User
    user = db.execute(
        select(User).where(User.id == current_user_id)
    ).scalar_one_or_none()
    
    if not user or not user.password_hash:  # type: ignore
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot unlink: no local password is set. Set a password first.",
        )
    
    # Delete identity
    db.delete(identity)
    db.commit()
    
    logger.info(f"User {current_user_id} unlinked OAuth provider {provider}")
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ===== Admin Recovery Routes =====

@router.post("/admin/recovery-login", response_model=TokenResponse)
async def admin_recovery_login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Admin-only recovery login endpoint.
    
    Identical to normal login but:
    - Explicitly named for admin recovery use
    - Requires admin role
    - Logs a warning for audit trail
    - NEVER redirects to OAuth (always accepts local credentials)
    
    NOTE: Should be rate-limited at reverse-proxy level.
    
    Args:
        request: Login request with username and password
        db: Database session
        
    Returns:
        TokenResponse with access token and user info
        
    Raises:
        HTTPException: If credentials invalid or user is not admin
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
    
    # Admin-only check
    user_service = UserService(db)
    user_dto = user_service.get_user_by_id(auth_result.user_id)
    
    if not user_dto or not user_dto.is_admin:
        logger.warning(f"Non-admin user {request.username} attempted admin recovery login")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    
    # Log recovery login for audit
    logger.warning(f"Admin recovery login used by {request.username}")
    
    # Create JWT token
    token = create_access_token(auth_result.user_id, auth_result.username)
    
    return TokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=UserResponse(
            id=auth_result.user_id,
            username=auth_result.username,
            nickname=auth_result.nickname,
            email=auth_result.email,
            display_name=auth_result.display_name,
        ),
    )


@router.post("/admin/set-local-password", response_model=UserResponse)
async def admin_set_local_password(
    request: SetLocalPasswordRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user),
) -> UserResponse:
    """Set local password for admin (for OIDC-only accounts adding recovery auth).
    
    Args:
        request: Password set request
        db: Database session
        current_user_id: Current authenticated user ID
        
    Returns:
        UserResponse with updated user info
    """
    user_service = UserService(db)
    
    # Get current user
    user_dto = user_service.get_user_by_id(current_user_id)
    
    if not user_dto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Admin-only
    if not user_dto.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin only",
        )
    
    # Set password
    try:
        user_service.set_password(current_user_id, request.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    
    logger.info(f"Admin {user_dto.username} set local password for recovery")
    
    # Return updated user info
    user_dto = user_service.get_user_by_id(current_user_id)
    
    return UserResponse(
        id=user_dto.id,  # type: ignore
        username=user_dto.username,  # type: ignore
        nickname=user_dto.nickname,  # type: ignore
        email=user_dto.email,  # type: ignore
        display_name=user_dto.display_name,  # type: ignore
    )
