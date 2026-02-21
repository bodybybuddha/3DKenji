"""Projects API endpoints for 3D Kenji."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.auth import get_current_user
from backend.db import get_db
from backend.services.project_service import ProjectDTO, ProjectService

# Initialize templates for HTML responses
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="/projects", tags=["projects"])


# Request Models
class CreateProjectRequest(BaseModel):
    """Request to create a new project."""

    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    custom_metadata: Optional[dict] = Field(None, description="Arbitrary JSON metadata")


class UpdateProjectRequest(BaseModel):
    """Request to update a project."""

    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    custom_metadata: Optional[dict] = Field(None)


# Response Models
class ProjectResponse(BaseModel):
    """Project response with metadata."""

    id: str
    owner_id: str
    title: str
    description: Optional[str]
    custom_metadata: dict
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectResponse]
    total: int
    skip: int
    limit: int


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Create a new project.

    Only authenticated users can create projects. The authenticated user
    becomes the project owner automatically.

    Args:
        request: CreateProjectRequest with title, description, metadata.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        ProjectResponse with created project data (201 Created).

    Raises:
        400: If project title is empty or invalid.
        401: If user is not authenticated.
    """
    try:
        service = ProjectService(session)
        project_dto = service.create_project(
            owner_id=current_user_id,
            title=request.title,
            description=request.description,
            custom_metadata=request.custom_metadata or {},
        )
        return ProjectResponse(**project_dto.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}",
        )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    format: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    request: Request = None,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProjectListResponse:
    """
    List projects owned by the authenticated user.

    Pagination is supported via skip and limit parameters.
    HTML format supported via ?format=html for HTMX integration.

    Args:
        format: Response format ('html' for HTMX, default returns JSON).
        skip: Number of projects to skip (default 0).
        limit: Maximum projects to return (default 100, max 1000).
        request: FastAPI Request object (injected).
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        ProjectListResponse with items, total, skip, limit (200 OK).
        If format=html, returns HTML snippet instead.

    Raises:
        401: If user is not authenticated.
    """
    # Clamp limit to reasonable max
    limit = min(limit, 1000)
    if limit < 0 or skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip and limit must be >= 0",
        )

    service = ProjectService(session)
    projects = service.list_user_projects(owner_id=current_user_id, skip=skip, limit=limit)

    # Return HTML fragment for HTMX
    if format == "html":
        return HTMLResponse(
            templates.get_template("fragments/projects-list.html").render(
                request=request,
                projects=[p.__dict__ for p in projects],
            )
        )

    return ProjectListResponse(
        items=[ProjectResponse(**p.__dict__) for p in projects],
        total=len(projects),
        skip=skip,
        limit=limit,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Get a project by ID.

    Only the project owner can view the project (for MVP, no sharing yet).

    Args:
        project_id: Project ID.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        ProjectResponse with project data (200 OK).

    Raises:
        401: If user is not authenticated.
        403: If user does not own the project.
        404: If project not found.
    """
    service = ProjectService(session)
    project = service.get_project_by_id(project_id)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    # Check ownership (MVP: only owner can view)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this project",
        )

    return ProjectResponse(**project.__dict__)


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> ProjectResponse:
    """
    Update a project.

    Only the project owner can update the project (for MVP, no sharing yet).

    Args:
        project_id: Project ID.
        request: UpdateProjectRequest with fields to update.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        ProjectResponse with updated project data (200 OK).

    Raises:
        400: If update request is invalid.
        401: If user is not authenticated.
        403: If user does not own the project.
        404: If project not found.
    """
    service = ProjectService(session)

    # Check ownership first
    project = service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this project",
        )

    try:
        updated = service.update_project(
            project_id=project_id,
            title=request.title,
            description=request.description,
            custom_metadata=request.custom_metadata,
        )
        return ProjectResponse(**updated.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: str,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> None:
    """
    Delete a project.

    Only the project owner can delete the project. Deletes the project
    and all associated models, media, and print jobs.

    Args:
        project_id: Project ID.
        current_user_id: ID of authenticated user (injected).
        session: Database session (injected).

    Returns:
        Empty response (204 No Content).

    Raises:
        401: If user is not authenticated.
        403: If user does not own the project.
        404: If project not found.
    """
    service = ProjectService(session)

    # Check ownership first
    project = service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this project",
        )

    if not service.delete_project(project_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )

# Modal endpoints for HTMX form loading
@router.get("/{project_id}/edit-modal", response_class=HTMLResponse)
async def get_edit_project_modal(
    project_id: str,
    request: Request,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> str:
    """
    Get the edit project modal form.
    
    Returns HTML for the edit project form modal.
    """
    service = ProjectService(session)
    project = service.get_project_by_id(project_id)
    
    if not project or project.owner_id != current_user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return templates.TemplateResponse("projects/form-modal.html", {
        "request": request,
        "project": project.__dict__,
    }).body.decode()


@router.get("/create-modal", response_class=HTMLResponse)
async def get_create_project_modal(
    request: Request,
    current_user_id: str = Depends(get_current_user),
) -> str:
    """Get the create project modal form."""
    return templates.TemplateResponse("projects/form-modal.html", {
        "request": request,
        "project": None,
    }).body.decode()