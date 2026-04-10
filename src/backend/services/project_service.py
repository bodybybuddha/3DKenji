"""Project service for project management."""

import re
import uuid
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.project import Project


def _slugify(title: str) -> str:
    """Derive a filesystem-safe slug from a project title (spec §2.3)."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = re.sub(r"-{2,}", "-", slug)
    slug = slug.strip("-")
    return (slug[:64]).rstrip("-") or "project"


@dataclass
class ProjectDTO:
    """Project domain transfer object."""

    id: str
    owner_id: str
    title: str
    slug: str
    category: str
    directory_path: Optional[str]
    disk_size_bytes: int
    is_archived: bool
    created_at: str
    updated_at: str


class ProjectService:
    """Service for project management operations."""

    def __init__(self, session: Session):
        """Initialize project service with database session."""
        self.session = session

    def create_project(
        self,
        owner_id: str,
        title: str,
        category: str = "Uncategorized",
    ) -> ProjectDTO:
        """Create a new project.

        Args:
            owner_id: ID of project owner (user)
            title: Project title
            category: Project category (directory group); defaults to "Uncategorized"

        Returns:
            ProjectDTO with created project data

        Raises:
            ValueError: If owner doesn't exist or slug collision cannot be resolved
        """
        from backend.models.user import User

        owner = self.session.execute(
            select(User).where(User.id == owner_id)
        ).scalar_one_or_none()

        if not owner:
            raise ValueError(f"User '{owner_id}' not found")

        # Generate a unique slug within (owner_id, category)
        base_slug = _slugify(title)
        slug = base_slug
        suffix = 1
        while True:
            existing = self.session.execute(
                select(Project).where(
                    Project.owner_id == owner_id,
                    Project.category == category,
                    Project.slug == slug,
                )
            ).scalar_one_or_none()
            if not existing:
                break
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        directory_path = f"Projects/{category}/{slug}"

        project = Project(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            title=title,
            slug=slug,
            category=category,
            directory_path=directory_path,
            disk_size_bytes=0,
            is_archived=False,
        )

        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)

        return self._to_dto(project)

    def get_project_by_id(self, project_id: str) -> Optional[ProjectDTO]:
        """Get project by ID.
        
        Args:
            project_id: Project ID
            
        Returns:
            ProjectDTO or None if not found
        """
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        return self._to_dto(project) if project else None

    def list_user_projects(
        self, owner_id: str, skip: int = 0, limit: int = 100
    ) -> list[ProjectDTO]:
        """List projects owned by a user.
        
        Args:
            owner_id: Owner user ID
            skip: Number of projects to skip
            limit: Maximum number of projects to return
            
        Returns:
            List of ProjectDTOs
        """
        projects = self.session.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        
        return [self._to_dto(project) for project in projects]

    def update_project(
        self,
        project_id: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
    ) -> ProjectDTO:
        """Update project title and/or category.

        Args:
            project_id: Project ID
            title: New title (if provided)
            category: New category (if provided)

        Returns:
            Updated ProjectDTO

        Raises:
            ValueError: If project not found
        """
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()

        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        if title is not None:
            project.title = title  # type: ignore[attr-defined]
            project.slug = _slugify(title)  # type: ignore[attr-defined]
        if category is not None:
            project.category = category  # type: ignore[attr-defined]

        # Update directory_path to reflect any title/category changes
        project.directory_path = f"Projects/{project.category}/{project.slug}"  # type: ignore[attr-defined]

        self.session.commit()
        self.session.refresh(project)

        return self._to_dto(project)

    def delete_project(self, project_id: str) -> bool:
        """Delete project and all associated models.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if deleted, False if not found
        """
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            return False

        self.session.delete(project)
        self.session.commit()
        return True

    def check_project_ownership(self, project_id: str, user_id: str) -> bool:
        """Check if user owns a project.
        
        Args:
            project_id: Project ID
            user_id: User ID
            
        Returns:
            True if user owns the project, False otherwise
        """
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        return bool(project is not None and project.owner_id == user_id)

    @staticmethod
    def _to_dto(project: Project) -> ProjectDTO:
        """Convert Project model to ProjectDTO."""
        return ProjectDTO(
            id=project.id,  # type: ignore[arg-type]
            owner_id=project.owner_id,  # type: ignore[arg-type]
            title=project.title,  # type: ignore[arg-type]
            slug=project.slug,  # type: ignore[arg-type]
            category=project.category,  # type: ignore[arg-type]
            directory_path=project.directory_path,  # type: ignore[arg-type]
            disk_size_bytes=project.disk_size_bytes or 0,  # type: ignore[arg-type]
            is_archived=bool(project.is_archived),  # type: ignore[arg-type]
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )
