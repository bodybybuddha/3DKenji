"""Project service for project management."""

import uuid
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.project import Project


@dataclass
class ProjectDTO:
    """Project domain transfer object."""

    id: str
    owner_id: str
    title: str
    description: Optional[str]
    custom_metadata: dict
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
        description: Optional[str] = None,
        custom_metadata: Optional[dict] = None,
    ) -> ProjectDTO:
        """Create a new project.
        
        Args:
            owner_id: ID of project owner (user)
            title: Project title
            description: Optional project description
            custom_metadata: Optional metadata dict
            
        Returns:
            ProjectDTO with created project data
            
        Raises:
            ValueError: If owner doesn't exist
        """
        # Verify owner exists (will be caught at DB level too)
        from backend.models.user import User
        
        owner = self.session.execute(
            select(User).where(User.id == owner_id)
        ).scalar_one_or_none()
        
        if not owner:
            raise ValueError(f"User '{owner_id}' not found")

        project = Project(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            title=title,
            description=description,
            custom_metadata=custom_metadata or {},
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
        description: Optional[str] = None,
        custom_metadata: Optional[dict] = None,
    ) -> ProjectDTO:
        """Update project.
        
        Args:
            project_id: Project ID
            title: New title (if provided)
            description: New description (if provided)
            custom_metadata: New metadata (if provided)
            
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
        if description is not None:
            project.description = description  # type: ignore[attr-defined]
        if custom_metadata is not None:
            project.custom_metadata = custom_metadata  # type: ignore[attr-defined]

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
        """Convert Project model to ProjectDTO.
        
        Args:
            project: Project model
            
        Returns:
            ProjectDTO
        """
        return ProjectDTO(
            id=project.id,  # type: ignore[arg-type]
            owner_id=project.owner_id,  # type: ignore[arg-type]
            title=project.title,  # type: ignore[arg-type]
            description=project.description,  # type: ignore[arg-type]
            custom_metadata=project.custom_metadata,  # type: ignore[arg-type]
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )
