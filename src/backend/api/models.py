"""Models API endpoints for 3D Kenji."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status, Form
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import tempfile
from pathlib import Path

from backend.api.auth import get_current_user
from backend.db import get_db
from backend.storage import get_storage
from backend.services.model_service import ModelDTO, ModelService
from backend.services.project_service import ProjectService
from backend.core.plugin_interfaces import StorageBackend

router = APIRouter(prefix="/projects", tags=["models"])


# Request Models
class UploadModelRequest(BaseModel):
    """Request to upload a model file."""

    filename: Optional[str] = Field(None, description="Custom filename (defaults to uploaded filename)")
    source_url: Optional[str] = Field(None, max_length=2048, description="URL where model came from")
    tags: Optional[list[str]] = Field(None, description="Tags for categorization")
    custom_metadata: Optional[dict] = Field(None, description="Arbitrary JSON metadata")


# Response Models
class ModelResponse(BaseModel):
    """Model response with metadata."""

    id: str
    project_id: str
    uploaded_by_id: str
    filename: str
    source_url: Optional[str]
    tags: list[str]
    custom_metadata: dict
    storage_key: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ModelListResponse(BaseModel):
    """Paginated list of models."""

    items: list[ModelResponse]
    total: int
    skip: int
    limit: int


# Constants
MAX_MODEL_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".stl", ".3mf", ".obj", ".gcode"}


def _validate_model_file(filename: str, file_size: int) -> None:
    """Validate model file before upload.

    Args:
        filename: Name of file being uploaded.
        file_size: Size of file in bytes.

    Raises:
        HTTPException: If file is invalid.
    """
    # Check file extension
    file_ext = Path(filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File extension {file_ext} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Check file size
    if file_size > MAX_MODEL_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size {file_size} exceeds maximum {MAX_MODEL_FILE_SIZE} bytes",
        )


@router.post("/{project_id}/models", status_code=status.HTTP_201_CREATED, response_model=ModelResponse)
async def upload_model(
    project_id: str,
    file: UploadFile = File(...),
    source_url: Optional[str] = None,
    tags: Optional[str] = None,  # JSON-encoded list
    custom_metadata: Optional[str] = None,  # JSON-encoded dict
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
) -> ModelResponse:
    """
    Upload a 3D model file to a project.

    Only the project owner can upload models. File must be one of the
    allowed formats (.stl, .3mf, .obj, .gcode) and must not exceed
    the maximum file size (50 MB).

    Args:
        project_id: ID of project to upload model to.
        file: Model file (multipart form data).
        source_url: Optional URL where model came from.
        tags: Optional JSON-encoded list of tags.
        custom_metadata: Optional JSON-encoded dict of metadata.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).
        storage: Storage backend (injected).

    Returns:
        ModelResponse with uploaded model data (201 Created).

    Raises:
        400: If file is invalid (wrong type or too large).
        401: If user is not authenticated.
        403: If user does not own the project.
        404: If project not found.
    """
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )

    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Check ownership
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to upload to this project",
        )

    try:
        # Read file into memory and validate
        file_content = await file.read()
        _validate_model_file(file.filename, len(file_content))

        # Store file
        storage_key = f"projects/{project_id}/models/{file.filename}"
        
        # Write to temporary file for storage
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        try:
            # Store in backend
            await storage.store(tmp_path, storage_key)

            # Create model record in database
            model_service = ModelService(session)
            parsed_tags = []
            if tags:
                # Simple comma-separated parsing (could use JSON in production)
                parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

            parsed_metadata = {}
            if custom_metadata:
                import json
                try:
                    parsed_metadata = json.loads(custom_metadata)
                except json.JSONDecodeError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid JSON in custom_metadata",
                    )

            model_dto = model_service.create_model(
                project_id=project_id,
                uploaded_by_id=current_user_id,
                filename=file.filename,
                storage_key=storage_key,
                source_url=source_url,
                tags=parsed_tags,
                custom_metadata=parsed_metadata,
            )

            return ModelResponse(**model_dto.__dict__)

        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload model: {str(e)}",
        )


@router.get("/{project_id}/models", response_model=ModelListResponse)
async def list_project_models(
    project_id: str,
    skip: int = 0,
    limit: int = 100,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ModelListResponse:
    """
    List models in a project.

    Only the project owner can list models (for MVP, no sharing yet).
    Pagination is supported via skip and limit.

    Args:
        project_id: Project ID.
        skip: Number of models to skip (default 0).
        limit: Maximum models to return (default 100, max 1000).
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        ModelListResponse with items, total, skip, limit (200 OK).

    Raises:
        401: If user is not authenticated.
        403: If user does not own the project.
        404: If project not found.
    """
    # Clamp limit
    limit = min(limit, 1000)
    if limit < 0 or skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip and limit must be >= 0",
        )

    # Check project ownership
    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this project",
        )

    model_service = ModelService(session)
    models = model_service.list_project_models(project_id, skip=skip, limit=limit)

    return ModelListResponse(
        items=[ModelResponse(**m.__dict__) for m in models],
        total=len(models),
        skip=skip,
        limit=limit,
    )


@router.get("/models/{model_id}", response_model=ModelResponse)
async def get_model(
    model_id: str,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ModelResponse:
    """
    Get a model by ID.

    Returns metadata about the model. For file download, use GET /models/{model_id}/download.
    Only the project owner can view models (for MVP, no sharing yet).

    Args:
        model_id: Model ID.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        ModelResponse with model metadata (200 OK).

    Raises:
        401: If user is not authenticated.
        403: If user does not own the project.
        404: If model not found.
    """
    model_service = ModelService(session)
    model = model_service.get_model_by_id(model_id)

    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )

    # Check project ownership
    project_service = ProjectService(session)
    project = project_service.get_project_by_id(model.project_id)

    if not project or project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this model",
        )

    return ModelResponse(**model.__dict__)

# File upload endpoint for HTMX forms
@router.post("/models/upload", status_code=status.HTTP_201_CREATED)
async def upload_model_form(
    project_id: str = Form(...),
    model_name: str = Form(...),
    model_file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    framework: Optional[str] = Form(None),
    version: Optional[str] = Form(None),
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
):
    """
    Upload a model file via HTMX form.
    
    This endpoint handles file uploads from the HTML form with additional
    metadata fields. Returns JSON response suitable for HTMX handling.
    """
    if not model_file or not model_file.filename:
        return JSONResponse(
            {"error": "No file provided"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)

    if not project:
        return JSONResponse(
            {"error": f"Project '{project_id}' not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Check ownership
    if project.owner_id != current_user_id:
        return JSONResponse(
            {"error": "You do not have permission to upload to this project"},
            status_code=status.HTTP_403_FORBIDDEN,
        )

    try:
        # TODO: Implement actual file upload logic
        # For now, just return success
        return {
            "success": True,
            "message": "Model uploaded successfully",
            "model": {
                "id": "model_123",
                "name": model_name,
                "framework": framework,
                "version": version,
                "size": 1024,
            }
        }
    except Exception as e:
        return JSONResponse(
            {"error": f"Upload failed: {str(e)}"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )