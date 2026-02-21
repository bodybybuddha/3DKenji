"""Password-based authentication plugin."""

from typing import Optional
from fastapi import FastAPI
from sqlalchemy.orm import Session

from backend.core.plugin_interfaces import AuthProvider, AuthResult, UserIdentity
from backend.core.auth import create_access_token, decode_token
from backend.services.user_service import UserService


class PasswordAuthProvider(AuthProvider):
    """Password-based authentication provider.
    
    Implements username/password authentication with bcrypt hashing.
    """

    name = "Password Auth"
    version = "1.0.0"
    author = "3D Kenji"
    auth_type = "password"

    def __init__(self, session: Session):
        """Initialize password auth provider.
        
        Args:
            session: Database session for user lookup
        """
        self.session = session
        self.user_service = UserService(session)

    async def register(self, app: FastAPI, config: dict) -> None:
        """Register the auth provider.
        
        Called during plugin initialization.
        """
        pass

    async def health_check(self) -> dict:
        """Check provider health.
        
        Returns:
            Dict with 'status' key
        """
        try:
            # Test that we can instantiate the service
            _ = UserService(self.session)
            return {"status": "healthy", "provider": "password_auth"}
        except Exception as e:
            return {"status": "unhealthy", "provider": "password_auth", "error": str(e)}

    async def authenticate(self, credentials: dict) -> AuthResult:
        """Authenticate user with username and password.
        
        Args:
            credentials: Dict with "username" and "password" keys
            
        Returns:
            AuthResult with user identity and token
            
        Raises:
            ValueError: If authentication fails
        """
        username = credentials.get("username")
        password = credentials.get("password")
        
        if not username or not password:
            raise ValueError("Username and password required")

        user_dto = self.user_service.verify_password(username, password)
        
        if not user_dto:
            raise ValueError("Invalid credentials")

        return AuthResult(
            user_id=user_dto.id,
            username=user_dto.username,
            email=user_dto.email,
            display_name=user_dto.display_name,
            scopes=[],
        )

    async def get_login_url(self, state: str, redirect_uri: str) -> Optional[str]:
        """Return None for password auth (not interactive).
        
        Args:
            state: OAuth state (not used for password auth)
            redirect_uri: OAuth redirect URI (not used for password auth)
            
        Returns:
            None
        """
        return None

    async def validate_token(self, token: str) -> Optional[UserIdentity]:
        """Validate a JWT token and return user identity.
        
        Args:
            token: JWT token
            
        Returns:
            UserIdentity if valid, None otherwise
        """
        try:
            token_payload = decode_token(token)
            
            # Verify user still exists
            user_dto = self.user_service.get_user_by_id(token_payload.user_id)
            
            if not user_dto or not user_dto.is_active:
                return None

            return UserIdentity(
                user_id=user_dto.id,
                username=user_dto.username,
                email=user_dto.email,
                display_name=user_dto.display_name,
            )
        except Exception:
            return None

    async def create_user(
        self, username: str, email: str, display_name: str, password: str
    ) -> UserIdentity:
        """Create a new user.
        
        Args:
            username: Username
            email: Email address
            display_name: Display name
            password: Plain text password
            
        Returns:
            UserIdentity with new user data
            
        Raises:
            ValueError: If username or email already exists
        """
        user_dto = self.user_service.create_user(
            username=username,
            email=email,
            display_name=display_name,
            password=password,
        )

        return UserIdentity(
            user_id=user_dto.id,
            username=user_dto.username,
            email=user_dto.email,
            display_name=user_dto.display_name,
        )

    async def update_password(self, user_id: str, new_password: str) -> UserIdentity:
        """Update user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password
            
        Returns:
            Updated UserIdentity
            
        Raises:
            ValueError: If user not found
        """
        user_dto = self.user_service.update_password(user_id, new_password)

        return UserIdentity(
            user_id=user_dto.id,
            username=user_dto.username,
            email=user_dto.email,
            display_name=user_dto.display_name,
        )

