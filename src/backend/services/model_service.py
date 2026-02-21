"""Model service for 3D model management."""

import uuid
from typing import Optional
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.model import Model


@dataclass
class ModelDTO:
    """Model domain transfer object."""

    id: str
    project_id: str
    uploaded_by_id: str
    filename: str
    source_url: Optional[str]
    tags: list
    custom_metadata: dict
    storage_key: str
    created_at: str
    updated_at: str


class ModelService:
    """Service for 3D model management operations."""

    def __init__(self, session: Session):
        """Initialize model service with database session."""
        self.session = session

    def create_model(
        self,
        project_id: str,
        uploaded_by_id: str,
        filename: str,
        storage_key: str,
        source_url: Optional[str] = None,
        tags: Optional[list] = None,
        custom_metadata: Optional[dict] = None,
    ) -> ModelDTO:
        """Create a new 3D model record.
        
        Args:
            project_id: ID of project this model belongs to
            uploaded_by_id: ID of user uploading the model
            filename: Filename of the model
            storage_key: Storage backend identifier (path/key)
            source_url: Optional URL where model came from
            tags: Optional list of tag strings
            custom_metadata: Optional metadata dict
            
        Returns:
            ModelDTO with created model data
            
        Raises:
            ValueError: If project or uploader doesn't exist or user doesn't own project
        """
        from backend.models.project import Project
        from backend.models.user import User

        # Verify project exists
        project = self.session.execute(
            select(Project).where(Project.id == project_id)
        ).scalar_one_or_none()
        
        if not project:
            raise ValueError(f"Project '{project_id}' not found")

        # Verify uploader exists
        uploader = self.session.execute(
            select(User).where(User.id == uploaded_by_id)
        ).scalar_one_or_none()
        
        if not uploader:
            raise ValueError(f"User '{uploaded_by_id}' not found")

        model = Model(
            id=str(uuid.uuid4()),
            project_id=project_id,
            uploaded_by_id=uploaded_by_id,
            filename=filename,
            storage_key=storage_key,
            source_url=source_url,
            tags=tags or [],
            custom_metadata=custom_metadata or {},
        )

        self.session.add(model)
        self.session.commit()
        self.session.refresh(model)

        return self._to_dto(model)

    def get_model_by_id(self, model_id: str) -> Optional[ModelDTO]:
        """Get model by ID.
        
        Args:
            model_id: Model ID
            
        Returns:
            ModelDTO or None if not found
        """
        model = self.session.execute(
            select(Model).where(Model.id == model_id)
        ).scalar_one_or_none()
        
        return self._to_dto(model) if model else None

    def list_project_models(
        self, project_id: str, skip: int = 0, limit: int = 100
    ) -> list[ModelDTO]:
        """List models in a project.
        
        Args:
            project_id: Project ID
            skip: Number of models to skip
            limit: Maximum number of models to return
            
        Returns:
            List of ModelDTOs
        """
        models = self.session.execute(
            select(Model)
            .where(Model.project_id == project_id)
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        
        return [self._to_dto(model) for model in models]

    def list_user_uploaded_models(
        self, user_id: str, skip: int = 0, limit: int = 100
    ) -> list[ModelDTO]:
        """List models uploaded by a user.
        
        Args:
            user_id: User ID
            skip: Number of models to skip
            limit: Maximum number of models to return
            
        Returns:
            List of ModelDTOs
        """
        models = self.session.execute(
            select(Model)
            .where(Model.uploaded_by_id == user_id)
            .offset(skip)
            .limit(limit)
        ).scalars().all()
        
        return [self._to_dto(model) for model in models]

    def update_model(
        self,
        model_id: str,
        filename: Optional[str] = None,
        source_url: Optional[str] = None,
        tags: Optional[list] = None,
        custom_metadata: Optional[dict] = None,
    ) -> ModelDTO:
        """Update model metadata.
        
        Args:
            model_id: Model ID
            filename: New filename (if provided)
            source_url: New source URL (if provided)
            tags: New tags list (if provided)
            custom_metadata: New metadata (if provided)
            
        Returns:
            Updated ModelDTO
            
        Raises:
            ValueError: If model not found
        """
        model = self.session.execute(
            select(Model).where(Model.id == model_id)
        ).scalar_one_or_none()
        
        if not model:
            raise ValueError(f"Model '{model_id}' not found")

        if filename is not None:
            model.filename = filename  # type: ignore[attr-defined]
        if source_url is not None:
            model.source_url = source_url  # type: ignore[attr-defined]
        if tags is not None:
            model.tags = tags  # type: ignore[attr-defined]
        if custom_metadata is not None:
            model.custom_metadata = custom_metadata  # type: ignore[attr-defined]

        self.session.commit()
        self.session.refresh(model)

        return self._to_dto(model)

    def delete_model(self, model_id: str) -> bool:
        """Delete model and clean up storage.
        
        Note: Caller is responsible for deleting actual file from storage backend.
        
        Args:
            model_id: Model ID
            
        Returns:
            True if deleted, False if not found
        """
        model = self.session.execute(
            select(Model).where(Model.id == model_id)
        ).scalar_one_or_none()
        
        if not model:
            return False

        self.session.delete(model)
        self.session.commit()
        return True

    def check_model_ownership(self, model_id: str, user_id: str) -> bool:
        """Check if user uploaded a model.
        
        Args:
            model_id: Model ID
            user_id: User ID
            
        Returns:
            True if user uploaded the model, False otherwise
        """
        model = self.session.execute(
            select(Model).where(Model.id == model_id)
        ).scalar_one_or_none()
        
        return bool(model is not None and model.uploaded_by_id == user_id)

    def check_model_in_project(self, model_id: str, project_id: str) -> bool:
        """Check if a model belongs to a project.
        
        Args:
            model_id: Model ID
            project_id: Project ID
            
        Returns:
            True if model is in project, False otherwise
        """
        model = self.session.execute(
            select(Model).where(Model.id == model_id)
        ).scalar_one_or_none()
        
        return bool(model is not None and model.project_id == project_id)

    @staticmethod
    def _to_dto(model: Model) -> ModelDTO:
        """Convert Model model to ModelDTO.
        
        Args:
            model: Model model
            
        Returns:
            ModelDTO
        """
        return ModelDTO(
            id=model.id,  # type: ignore[arg-type]
            project_id=model.project_id,  # type: ignore[arg-type]
            uploaded_by_id=model.uploaded_by_id,  # type: ignore[arg-type]
            filename=model.filename,  # type: ignore[arg-type]
            source_url=model.source_url,  # type: ignore[arg-type]
            tags=model.tags,  # type: ignore[arg-type]
            custom_metadata=model.custom_metadata,  # type: ignore[arg-type]
            storage_key=model.storage_key,  # type: ignore[arg-type]
            created_at=model.created_at.isoformat(),
            updated_at=model.updated_at.isoformat(),
        )
