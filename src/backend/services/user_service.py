"""User service for user management."""

import re
import shutil
import uuid
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select
import bcrypt

from backend.models.user import User
from backend.models.project import Project
from backend.models.api_key import APIKey
from backend.services.project_directory import get_projects_dir


@dataclass
class UserDTO:
    """User domain transfer object."""

    id: str
    username: str
    nickname: str
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
        password: Optional[str] = None,
        nickname: Optional[str] = None,
        is_admin: bool = False,
        is_active: bool = True,
    ) -> UserDTO:
        """Create a new user with optional password.
        
        Args:
            username: Unique username
            email: Unique email address
            display_name: Display name
            password: Plain text password (will be hashed). None for OIDC-only accounts.
            nickname: Optional nickname for filesystem identity
            is_admin: Whether user is admin
            is_active: Whether user is active
            
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

        # Resolve a collision-safe nickname for storage identity.
        base_nickname = self.normalize_nickname(nickname or username)
        unique_nickname = self._ensure_unique_nickname(base_nickname)

        # Hash password if provided (None for OIDC-only accounts)
        password_hash = self._hash_password(password) if password else None

        # Create user
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            nickname=unique_nickname,
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

    def get_user_by_id_orm(self, user_id: str) -> Optional[User]:
        """Get User ORM object by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User ORM object or None if not found
        """
        return self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()

    def set_password(self, user_id: str, plain_password: str) -> None:
        """Set password for a user (for admin recovery or OIDC users adding local auth).
        
        Args:
            user_id: User ID
            plain_password: New plain text password (will be hashed)
            
        Raises:
            ValueError: If user not found or password invalid
        """
        if len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters")

        user = self.get_user_by_id_orm(user_id)
        if not user:
            raise ValueError(f"User '{user_id}' not found")

        user.password_hash = self._hash_password(plain_password)  # type: ignore[attr-defined]
        self.session.commit()

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

        # OIDC-only accounts with no password cannot authenticate via password
        if not user.password_hash:  # type: ignore[attr-defined]
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

    def update_profile(
        self,
        user_id: str,
        *,
        email: str,
        display_name: str,
        nickname: str,
    ) -> UserDTO:
        """Update profile fields and migrate owner filesystem path when nickname changes."""
        user = self.session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if not user:
            raise ValueError(f"User '{user_id}' not found")

        normalized_nickname = self.normalize_nickname(nickname)

        duplicate_email = self.session.execute(
            select(User).where(User.email == email, User.id != user_id)
        ).scalar_one_or_none()
        if duplicate_email:
            raise ValueError(f"Email '{email}' already exists")

        duplicate_nickname = self.session.execute(
            select(User).where(User.nickname == normalized_nickname, User.id != user_id)
        ).scalar_one_or_none()
        if duplicate_nickname:
            raise ValueError(f"Nickname '{normalized_nickname}' already exists")

        old_nickname = str(user.nickname)
        rename_performed = False
        rename_source: Optional[Path] = None
        rename_target: Optional[Path] = None

        if old_nickname != normalized_nickname:
            rename_source, rename_target, rename_performed = self._migrate_owner_storage_root(
                owner_id=str(user.id),
                old_nickname=old_nickname,
                new_nickname=normalized_nickname,
            )

        user.email = email  # type: ignore[attr-defined]
        user.display_name = display_name  # type: ignore[attr-defined]
        user.nickname = normalized_nickname  # type: ignore[attr-defined]

        projects = self.session.execute(
            select(Project).where(Project.owner_id == user_id)
        ).scalars().all()
        for project in projects:
            project.directory_path = f"Projects/{normalized_nickname}/{project.slug}"  # type: ignore[attr-defined]

        try:
            self.session.commit()
            self.session.refresh(user)
        except Exception:
            self.session.rollback()
            if rename_performed and rename_source and rename_target:
                self._rollback_owner_storage_rename(rename_source, rename_target)
            raise

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
    def normalize_nickname(value: str) -> str:
        """Normalize nickname into a filesystem-safe, user-friendly segment."""
        nickname = (value or "").strip().lower()
        nickname = re.sub(r"[^a-z0-9_-]+", "-", nickname)
        nickname = re.sub(r"-{2,}", "-", nickname).strip("-_")

        if len(nickname) < 3:
            raise ValueError("Nickname must be at least 3 characters")
        if len(nickname) > 64:
            nickname = nickname[:64].rstrip("-_")
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", nickname):
            raise ValueError("Nickname can only contain lowercase letters, numbers, hyphens, and underscores")

        return nickname

    def _ensure_unique_nickname(self, base_nickname: str) -> str:
        """Return a unique nickname by appending a numeric suffix when needed."""
        candidate = base_nickname
        counter = 1
        while self.session.execute(
            select(User).where(User.nickname == candidate)
        ).scalar_one_or_none():
            counter += 1
            suffix = f"-{counter}"
            trimmed = base_nickname[: max(1, 64 - len(suffix))].rstrip("-_")
            candidate = f"{trimmed}{suffix}"
        return candidate

    @staticmethod
    def _rollback_owner_storage_rename(source_root: Path, destination_root: Path) -> None:
        """Best-effort rollback when DB commit fails after filesystem move."""
        try:
            if destination_root.exists() and not source_root.exists():
                source_root.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(destination_root), str(source_root))
        except Exception:
            pass

    def _migrate_owner_storage_root(
        self,
        *,
        owner_id: str,
        old_nickname: str,
        new_nickname: str,
    ) -> tuple[Optional[Path], Optional[Path], bool]:
        """Rename owner root directory from old nickname (or owner_id) to new nickname."""
        projects_root = get_projects_dir()
        legacy_owner_root = projects_root / owner_id
        old_nickname_root = projects_root / old_nickname
        new_nickname_root = projects_root / new_nickname

        source_root: Optional[Path] = None
        if old_nickname_root.exists():
            source_root = old_nickname_root
        elif legacy_owner_root.exists() and legacy_owner_root != new_nickname_root:
            source_root = legacy_owner_root

        if not source_root or source_root == new_nickname_root:
            return None, None, False

        if new_nickname_root.exists():
            raise ValueError(
                f"Cannot change nickname: storage directory '{new_nickname_root.name}' already exists"
            )

        new_nickname_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_root), str(new_nickname_root))
        return source_root, new_nickname_root, True

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
            nickname=user.nickname,  # type: ignore[arg-type]
            email=user.email,  # type: ignore[arg-type]
            display_name=user.display_name,  # type: ignore[arg-type]
            is_admin=bool(user.is_admin),  # type: ignore[attr-defined]
            is_active=bool(user.is_active),  # type: ignore[attr-defined]
            created_at=user.created_at.isoformat(),
            updated_at=user.updated_at.isoformat(),
        )
