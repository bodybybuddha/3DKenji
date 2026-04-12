"""Project service for project management."""

import re
import uuid
import shutil
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.project import Project
from backend.models.project_collaborator import ProjectCollaborator
from backend.services.project_directory import (
    resolve_owner_storage_segment,
    service_for_project_owner,
)


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
    visibility: str
    directory_path: Optional[str]
    disk_size_bytes: int
    is_archived: bool
    deletion_policy: str
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
        visibility: str = "private",
        description: str = "",
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

        # Generate a unique slug within owner scope.
        base_slug = _slugify(title)
        slug = base_slug
        suffix = 1
        while True:
            existing = self.session.execute(
                select(Project).where(
                    Project.owner_id == owner_id,
                    Project.slug == slug,
                )
            ).scalar_one_or_none()
            if not existing:
                break
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        owner_segment = resolve_owner_storage_segment(self.session, owner_id)
        directory_path = f"Projects/{owner_segment}/{slug}"

        project = Project(
            id=str(uuid.uuid4()),
            owner_id=owner_id,
            title=title,
            slug=slug,
            category=category,
            visibility=visibility,
            directory_path=directory_path,
            disk_size_bytes=0,
            is_archived=False,
        )

        directory_service = service_for_project_owner(
            self.session,
            owner_id,
            slug,
            legacy_segment=category,
        )
        directory_already_existed = directory_service.project_directory_exists()

        try:
            directory_service.create_project_directory(title=title, description=description)

            self.session.add(project)
            self.session.commit()
            self.session.refresh(project)
        except Exception:
            self.session.rollback()
            # If we created a new directory but DB commit failed, clean it up.
            if not directory_already_existed and directory_service.project_directory_exists():
                directory_service.delete_project_directory()
            raise

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
            .where(Project.is_archived == False)
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        
        return [self._to_dto(project) for project in projects]

    def list_accessible_projects(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> list[ProjectDTO]:
        """List projects a user can access (owned, collaborator, public)."""
        owned = self.session.execute(
            select(Project)
            .where(Project.owner_id == user_id)
            .where(Project.is_archived == False)
        ).scalars().all()
        collaborator_projects = self.session.execute(
            select(Project)
            .join(ProjectCollaborator, ProjectCollaborator.project_id == Project.id)
            .where(ProjectCollaborator.user_id == user_id)
            .where(Project.is_archived == False)
        ).scalars().all()
        public_projects = self.session.execute(
            select(Project)
            .where(Project.visibility == "public")
            .where(Project.is_archived == False)
        ).scalars().all()

        deduped: dict[str, Project] = {}
        for project in owned + collaborator_projects + public_projects:
            deduped[project.id] = project

        ordered = sorted(
            deduped.values(),
            key=lambda p: p.updated_at,
            reverse=True,
        )
        window = ordered[skip : skip + limit]
        return [self._to_dto(project) for project in window]

    def update_project(
        self,
        project_id: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
        visibility: Optional[str] = None,
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

        old_slug = project.slug
        old_category = project.category
        old_directory_path = project.directory_path

        if title is not None:
            project.title = title  # type: ignore[attr-defined]
            project.slug = _slugify(title)  # type: ignore[attr-defined]
        if category is not None:
            project.category = category  # type: ignore[attr-defined]
        if visibility is not None:
            project.visibility = visibility  # type: ignore[attr-defined]

        # Update directory_path to reflect title changes using owner-scoped storage.
        owner_segment = resolve_owner_storage_segment(self.session, str(project.owner_id))
        project.directory_path = f"Projects/{owner_segment}/{project.slug}"  # type: ignore[attr-defined]

        old_dir = service_for_project_owner(
            self.session,
            str(project.owner_id),
            str(old_slug),
            legacy_segment=str(old_category),
        )._root
        new_dir = service_for_project_owner(
            self.session,
            str(project.owner_id),
            str(project.slug),
        )._root  # type: ignore[arg-type]

        if old_dir != new_dir and old_dir.exists():
            new_dir.parent.mkdir(parents=True, exist_ok=True)
            if new_dir.exists():
                raise ValueError(
                    f"Cannot move project directory: destination '{new_dir}' already exists"
                )
            shutil.move(str(old_dir), str(new_dir))

        if old_dir == new_dir and not new_dir.exists():
            # Backfill missing directory for legacy projects.
            service_for_project_owner(
                self.session,
                str(project.owner_id),
                str(project.slug),
            ).create_project_directory(
                title=str(project.title), description=""
            )

        try:
            self.session.commit()
            self.session.refresh(project)
        except Exception:
            self.session.rollback()
            # Attempt best-effort rollback of filesystem rename.
            if old_dir != new_dir and new_dir.exists() and not old_dir.exists():
                try:
                    old_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(new_dir), str(old_dir))
                except Exception:
                    pass
            project.directory_path = old_directory_path
            raise

        return self._to_dto(project)

    def delete_project(self, project_id: str) -> bool:
        """Delete project according to its deletion_policy setting.
        
        If deletion_policy is 'archive' (default), move project to archive category.
        If deletion_policy is 'hard_delete', permanently remove project and files.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if deleted/archived, False if not found
        """
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            return False

        # Apply deletion policy
        policy = getattr(project, 'deletion_policy', 'archive')
        if policy == 'hard_delete':
            return self._hard_delete_project(project_id)
        else:
            return self._archive_project(project_id)

    def _archive_project(self, project_id: str) -> bool:
        """Move project to archive category without deleting files.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if archived, False if not found
        """
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            return False

        # Move to archive category
        old_slug = project.slug
        project.is_archived = True
        owner_segment = resolve_owner_storage_segment(self.session, str(project.owner_id))
        project.directory_path = f"Projects/{owner_segment}/{old_slug}"
        
        self.session.commit()
        
        return True

    def _hard_delete_project(self, project_id: str) -> bool:
        """Permanently delete project and all files (no archive).
        
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

        directory_service = service_for_project_owner(
            self.session,
            str(project.owner_id),
            str(project.slug),
            legacy_segment=str(project.category),
        )

        self.session.delete(project)
        self.session.commit()

        # Best-effort filesystem cleanup after successful DB delete.
        if directory_service.project_directory_exists():
            directory_service.delete_project_directory()
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

    def _resolve_disk_size_bytes(self, project: Project) -> int:
        """Resolve project disk usage from filesystem, falling back to DB value."""
        db_size = int(project.disk_size_bytes or 0)
        try:
            directory_service = service_for_project_owner(
                self.session,
                str(project.owner_id),
                str(project.slug),
                legacy_segment=str(project.category),
            )
            if not directory_service.project_directory_exists():
                return db_size
            return directory_service.compute_disk_size()
        except Exception:
            # Never fail API serialization due to filesystem sizing issues.
            return db_size

    def _to_dto(self, project: Project) -> ProjectDTO:
        """Convert Project model to ProjectDTO."""
        return ProjectDTO(
            id=project.id,  # type: ignore[arg-type]
            owner_id=project.owner_id,  # type: ignore[arg-type]
            title=project.title,  # type: ignore[arg-type]
            slug=project.slug,  # type: ignore[arg-type]
            category=project.category,  # type: ignore[arg-type]
            visibility=getattr(project, "visibility", "private"),  # type: ignore[arg-type]
            directory_path=project.directory_path,  # type: ignore[arg-type]
            disk_size_bytes=self._resolve_disk_size_bytes(project),
            is_archived=bool(project.is_archived),  # type: ignore[arg-type]
            deletion_policy=getattr(project, 'deletion_policy', 'archive'),  # type: ignore[arg-type]
            created_at=project.created_at.isoformat(),
            updated_at=project.updated_at.isoformat(),
        )
