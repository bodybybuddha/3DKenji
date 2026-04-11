"""Projects API endpoints for 3D Kenji."""

import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.api.auth import get_current_user, require_scopes
from backend.db import get_db
from backend.core.validation import CreateProjectRequest as ValidatedProjectRequest, format_validation_errors, sanitize_text_input
from backend.services.project_service import ProjectDTO, ProjectService
from backend.api.frontend import templates

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
    """Project response matching the Project model structure."""

    id: str
    owner_id: str
    title: str
    slug: str
    category: str
    directory_path: Optional[str] = None
    disk_size_bytes: Optional[int] = 0
    is_archived: bool = False

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectResponse]
    total: int
    skip: int
    limit: int


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    req: Request,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    visibility: Optional[str] = Form("private"),
    tags: Optional[str] = Form(None),
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """
    Create a new project.
    
    Handles both form submissions (for HTMX) and JSON API requests.
    Form field 'name' maps to 'title' internally.
    JSON should use 'title' field directly.
    """
    try:
        # Check content type to determine request format
        content_type = req.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # Handle JSON request
            body = await req.json()
            title = body.get("title") or body.get("name")  # Support both field names
            desc = body.get("description")
            metadata = body.get("custom_metadata", {})
            
            if not title:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="title or name field is required"
                )
            
            # Validate title length and content
            title_stripped = title.strip()
            if not title_stripped:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project title cannot be empty or whitespace only"
                )
            if len(title_stripped) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project title must be at least 2 characters"
                )
            if len(title_stripped) > 255:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Project title must be at most 255 characters"
                )
            
            # Sanitize inputs to prevent XSS
            try:
                title = sanitize_text_input(title_stripped, "Project title")
                if desc:
                    desc = sanitize_text_input(desc, "Project description")
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        else:
            # Handle form request
            if not name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="name field is required"
                )
            try:
                validated = ValidatedProjectRequest(
                    name=name,
                    description=description,
                    visibility=visibility or "private",
                )
                title = sanitize_text_input(validated.name, "Project title")
                desc = (
                    sanitize_text_input(validated.description, "Project description")
                    if validated.description
                    else None
                )
            except ValidationError as e:
                errors = format_validation_errors(e)
                return templates.TemplateResponse(
                    "fragments/error-alert.html",
                    {
                        "request": req,
                        "message": "Validation failed",
                        "errors": errors,
                    },
                    status_code=400,
                )
            except ValueError as e:
                return HTMLResponse(
                    content=f'<div class="alert alert-danger">Error: {str(e)}</div>',
                    status_code=400,
                )

            metadata = {
                "visibility": validated.visibility,
                "tags": tags.split(",") if tags else []
            }
        
        service = ProjectService(session)
        # Extract category from metadata if present, otherwise default to "Uncategorized"
        category = metadata.get("visibility", "Uncategorized") if isinstance(metadata, dict) else "Uncategorized"
        project_dto = service.create_project(
            owner_id=current_user_id,
            title=title,
            category=category,
            description=desc or "",
        )
        
        # Return appropriate response based on content type
        if "application/json" in content_type:
            return ProjectResponse(**project_dto.__dict__)
        else:
            # Return HTML response for HTMX
            return HTMLResponse(
                content='<div class="alert alert-success">Project created successfully</div>',
                status_code=201
            )
    except HTTPException:
        raise
    except ValueError as e:
        if "application/json" in req.headers.get("content-type", ""):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        return HTMLResponse(
            content=f'<div class="alert alert-danger">Error: {str(e)}</div>',
            status_code=400
        )
    except Exception as e:
        if "application/json" in req.headers.get("content-type", ""):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project: {str(e)}"
            )
        return HTMLResponse(
            content=f'<div class="alert alert-danger">Failed to create project: {str(e)}</div>',
            status_code=500
        )


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    format: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    request: Request = None,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
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
    current_user_id: str = Depends(require_scopes(["read:projects"])),
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
    current_user_id: str = Depends(require_scopes(["write:projects"])),
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

    # Sanitize inputs to prevent XSS
    sanitized_title = request.title
    sanitized_category = None
    
    try:
        if request.title:
            sanitized_title = sanitize_text_input(request.title, "Project title")
        if request.custom_metadata:
            requested_category = request.custom_metadata.get("category") or request.custom_metadata.get("visibility")
            if requested_category:
                sanitized_category = sanitize_text_input(str(requested_category), "Project category")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    try:
        updated = service.update_project(
            project_id=project_id,
            title=sanitized_title,
            category=sanitized_category,
        )
        return ProjectResponse(**updated.__dict__)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}",
        )


@router.put("/{project_id}", response_class=HTMLResponse)
async def update_project_form(
    project_id: str,
    request: Request,
    name: str = Form(...),
    visibility: Optional[str] = Form(None),
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> HTMLResponse:
    """Update project from HTMX form submission."""
    service = ProjectService(session)
    project = service.get_project_by_id(project_id)

    if not project:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": "Project not found", "errors": {}},
            status_code=404,
        )

    if project.owner_id != current_user_id:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": "You do not have permission to update this project", "errors": {}},
            status_code=403,
        )

    try:
        if not name or not name.strip():
            raise ValueError("Project name is required")

        sanitized_name = sanitize_text_input(name.strip(), "Project title")
        sanitized_category = sanitize_text_input(visibility, "Project category") if visibility else None

        service.update_project(
            project_id=project_id,
            title=sanitized_name,
            category=sanitized_category,
        )

        return templates.TemplateResponse(
            "fragments/success-alert.html",
            {"request": request, "message": "Project updated successfully"},
            status_code=200,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": str(e), "errors": {}},
            status_code=400,
        )
    except Exception as e:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": "Failed to update project", "errors": {"general": [str(e)]}},
            status_code=500,
        )


@router.delete("/{project_id}")
async def delete_project(
    request: Request,
    project_id: str,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> Response:
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

    if request.headers.get("HX-Request") == "true":
        return HTMLResponse(content="", status_code=200)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

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

# Form validation endpoints
@router.post("/validate/create", response_class=HTMLResponse)
async def validate_create_project(
    request: Request,
    name: str = None,
    description: str = None,
    visibility: str = None,
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    """Validate project creation form."""
    try:
        # Validate inputs
        validated = ValidatedProjectRequest(
            name=name or "",
            description=description,
            visibility=visibility or "private",
        )
        
        # Create project
        service = ProjectService(session)
        project_dto = service.create_project(
            owner_id=current_user_id,
            title=validated.name,
            description=validated.description,
            custom_metadata={"visibility": validated.visibility},
        )
        
        return JSONResponse({
            "success": True,
            "message": "Project created successfully",
            "project_id": project_dto.id,
        })
    
    except ValidationError as e:
        errors = format_validation_errors(e)
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Validation failed",
            "errors": errors,
        }, status_code=400)
    except Exception as e:
        return templates.TemplateResponse("fragments/error-alert.html", {
            "request": request,
            "message": "Failed to create project",
            "errors": {"general": [str(e)]},
        }, status_code=500)
