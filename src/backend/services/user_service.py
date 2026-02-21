"""User service for user management."""

import uuid
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select
import bcrypt

from backend.models.user import User
from backend.models.api_key import APIKey


@dataclass
class UserDTO:
    """User domain transfer object."""

    id: str
    username: str
    email: str
    display_name: str
    is_admin: bool
    is_active: bool
    created_at: str
    updated_at: str


class UserService:
    """Service for user management operations."""

    def __init__(self, session: Session):
        """Initialize user service with database session."""
        self.session = session

    def create_user(
        self,
        username: str,
        email: str,
        display_name: str,
        password: str,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> UserDTO:
        """Create a new user with password.
        
        Args:
            username: Unique username
            email: Unique email address
            display_name: Display name
            password: Plain text password (will be hashed)
            
        Returns:
            UserDTO with created user data
            
        Raises:
            ValueError: If username or email already exists
        """
        # Check if username exists
        existing_user = self.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        if existing_user:
            raise ValueError(f"Username '{username}' already exists")

        # Check if email exists
        existing_user = self.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        if existing_user:
            raise ValueError(f"Email '{email}' already exists")

        # Hash password
        password_hash = self._hash_password(password)

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            is_admin=is_admin,
            is_active=is_active,
        )

        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)

        return self._to_dto(user)

    def get_user_by_id(self, user_id: str) -> Optional[UserDTO]:
        """Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            UserDTO or None if not found
        """
        user = self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        
        return self._to_dto(user) if user else None

    def get_user_by_username(self, username: str) -> Optional[UserDTO]:
        """Get user by username.
        
        Args:
            username: Username
            
        Returns:
            UserDTO or None if not found
        """
        user = self.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        
        return self._to_dto(user) if user else None

    def get_user_by_email(self, email: str) -> Optional[UserDTO]:
        """Get user by email.
        
        Args:
            email: Email address
            
        Returns:
            UserDTO or None if not found
        """
        user = self.session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        
        return self._to_dto(user) if user else None

    def verify_password(self, username: str, password: str) -> Optional[UserDTO]:
        """Verify user password.
        
        Args:
            username: Username
            password: Plain text password to verify
            
        Returns:
            UserDTO if password matches, None otherwise
        """
        user = self.session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        
        if not user:
            return None

        if not user.is_active:  # type: ignore[attr-defined]
            return None

        if self._verify_password(password, user.password_hash):  # type: ignore[arg-type]
            return self._to_dto(user)

        return None

    def update_display_name(self, user_id: str, display_name: str) -> UserDTO:
        """Update user display name.
        
        Args:
            user_id: User ID
            display_name: New display name
            
        Returns:
            Updated UserDTO
            
        Raises:
            ValueError: If user not found
        """
        user = self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User '{user_id}' not found")

        user.display_name = display_name  # type: ignore[attr-defined]
        self.session.commit()
        self.session.refresh(user)

        return self._to_dto(user)

    def update_password(self, user_id: str, new_password: str) -> UserDTO:
        """Update user password.
        
        Args:
            user_id: User ID
            new_password: New plain text password
            
        Returns:
            Updated UserDTO
            
        Raises:
            ValueError: If user not found
        """
        user = self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User '{user_id}' not found")

        user.password_hash = self._hash_password(new_password)  # type: ignore[attr-defined]
        self.session.commit()
        self.session.refresh(user)

        return self._to_dto(user)

    def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deleted, False if not found
        """
        user = self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        
        if not user:
            return False

        self.session.delete(user)
        self.session.commit()
        return True

    def list_users(self, skip: int = 0, limit: int = 100) -> list[UserDTO]:
        """List users with pagination.
        
        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return
            
        Returns:
            List of UserDTOs
        """
        users = self.session.execute(
            select(User).offset(skip).limit(limit)
        ).scalars().all()
        
        return [self._to_dto(user) for user in users]

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode(), salt).decode()

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            password: Plain text password
            password_hash: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(password.encode(), password_hash.encode())

    @staticmethod
    def _to_dto(user: User) -> UserDTO:
        """Convert User model to UserDTO.
        
        Args:
            user: User model
            
        Returns:
            UserDTO
        """
        return UserDTO(
            id=user.id,  # type: ignore[arg-type]
            username=user.username,  # type: ignore[arg-type]
            email=user.email,  # type: ignore[arg-type]
            display_name=user.display_name,  # type: ignore[arg-type]
            is_admin=bool(user.is_admin),  # type: ignore[attr-defined]
            is_active=bool(user.is_active),  # type: ignore[attr-defined]
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
