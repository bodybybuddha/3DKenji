"""Projects API endpoints for 3D Kenji."""

import html
import json
import mimetypes
import os
import secrets
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import quote_plus
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, Response, FileResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.api.auth import get_current_user, require_scopes
from backend.db import get_db
from backend.core.validation import CreateProjectRequest as ValidatedProjectRequest, format_validation_errors, sanitize_text_input
from backend.models.project import Project
from backend.models.project_invitation import ProjectInvitation
from backend.models.user import User
from backend.services.project_directory import (
    PathNotFoundError,
    PathTraversalError,
    UnsafeFilenameError,
    service_for_project_owner,
)
from backend.services.markdown_service import render_markdown
from backend.services.project_access import ProjectAccessService
from backend.services.email_service import send_project_invitation_email, EmailDeliveryError
from backend.services.project_service import ProjectDTO, ProjectService
from backend.api.frontend import templates

router = APIRouter(prefix="/projects", tags=["projects"])

MAX_PROJECT_FILE_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_TEXT_EDITOR_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
EDITABLE_EXTENSIONS = {
    "txt", "md", "markdown", "rtf", "log", "json", "yaml", "yml", "csv",
    "ini", "cfg", "conf", "toml", "xml", "html", "css", "js", "ts", "py",
    "gcode", "sql", "sh",
}
CREATEABLE_FILE_TEMPLATES = {
    "md": "# Title\n\nStart writing here.\n",
    "txt": "",
    "rtf": "{\\rtf1\\ansi\\deff0 {\\fonttbl{\\f0 Arial;}}\\f0\\fs24 New document\\par\n}",
    "json": "{\n  \"key\": \"value\"\n}\n",
    "yaml": "key: value\n",
    "csv": "column1,column2\n",
    "log": "",
    "py": "# New Python file\n",
    "sql": "-- New SQL file\n",
    "html": "<!doctype html>\n<html>\n<head><title>New File</title></head>\n<body>\n\n</body>\n</html>\n",
}


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
    tags: list[str] = Field(default_factory=list)
    visibility: str = "private"
    directory_path: Optional[str] = None
    disk_size_bytes: Optional[int] = 0
    is_archived: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    """Paginated list of projects."""

    items: list[ProjectResponse]
    total: int
    skip: int
    limit: int


class CollaboratorRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: str = Field(..., pattern="^(viewer|editor)$")


class CollaboratorResponse(BaseModel):
    user_id: str
    role: str
    granted_by_id: str
    created_at: datetime


class InvitationRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    role: str = Field("viewer", pattern="^(viewer|editor)$")
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationResponse(BaseModel):
    invitation_id: str
    invited_email: str
    role: str
    expires_at: datetime
    token: str


class InvitationSummaryResponse(BaseModel):
    invitation_id: str
    invited_email: str
    role: str
    expires_at: datetime
    accepted_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime


class InvitationUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(viewer|editor)$")


class PendingInvitationResponse(BaseModel):
    invitation_id: str
    project_id: str
    project_title: str
    invited_email: str
    role: str
    expires_at: datetime
    created_at: datetime


class UpdateProjectFileContentRequest(BaseModel):
    """Request payload for text file editor saves."""

    path: str = Field(..., min_length=1)
    content: str = Field(default="")


class MarkdownPreviewRequest(BaseModel):
    """Request payload for markdown preview rendering."""

    content: str = Field(default="")


class CreateProjectFileRequest(BaseModel):
    """Request payload for creating a new file from supported templates."""

    path: str = Field(default="")
    name: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., min_length=1, max_length=20)

class CreateProjectFolderRequest(BaseModel):
    """Request payload for creating a folder in the current directory."""

    path: str = Field(default="")
    name: str = Field(..., min_length=1, max_length=255)


class RenameProjectPathRequest(BaseModel):
    """Request payload for renaming an existing file/folder path."""

    path: str = Field(..., min_length=1)
    new_name: str = Field(..., min_length=1, max_length=255)


class MoveProjectPathsRequest(BaseModel):
    """Request payload for moving one or more paths into a destination folder."""

    paths: list[str] = Field(..., min_length=1)
    destination_path: str = Field(default="")
RESERVED_PROJECT_FILES = {"ProjectInfo.md", "PrintHistory.md"}


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def _is_project_info_path(path: str) -> bool:
    """Return True when path points to ProjectInfo.md at project root."""
    normalized = str(PurePosixPath(path.replace("\\", "/"))).lstrip("/")
    return normalized == "ProjectInfo.md"


def _resolve_project_for_owner(
    project_id: str,
    owner_id: str,
    session: Session,
):
    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    if project.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this project",
        )
    return project


def _resolve_project_model(project_id: str, session: Session) -> Project:
    project = session.execute(select(Project).where(Project.id == project_id)).scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found",
        )
    return project


async def _resolve_viewer_info(
    request: Request,
    extension: str,
    *,
    refresh_if_missing: bool = False,
) -> Optional[dict]:
    manager = getattr(request.app.state, "plugin_manager", None)
    if manager is None:
        return None

    normalized_extension = extension.lower().lstrip(".")
    if not normalized_extension:
        return None

    viewer = manager.get_viewer_for_extension(normalized_extension)
    if viewer is None and refresh_if_missing:
        try:
            await manager.load_plugins(request.app, {})
        except Exception:
            viewer = None
        else:
            viewer = manager.get_viewer_for_extension(normalized_extension)

    if viewer is None:
        return None
    return {
        "viewer_id": viewer.viewer_id,
        "plugin_id": viewer.plugin_id,
        "name": viewer.name,
        "extensions": viewer.extensions,
        "has_js": viewer.js_file is not None,
        "backend_entrypoint": viewer.backend_entrypoint,
    }


def _guess_raw_media_type(path: str) -> str:
    extension = os.path.splitext(path)[1].lower()
    if extension == ".stl":
        return "model/stl"
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def _is_editable_extension(extension: str) -> bool:
    return extension.lower().lstrip(".") in EDITABLE_EXTENSIONS


def _normalize_file_type(file_type: str) -> str:
    return file_type.lower().lstrip(".").strip()

def _is_reserved_project_file_path(path: str) -> bool:
    normalized = path.strip("/")
    if not normalized:
        return False
    if "/" in normalized:
        return False
    return normalized in RESERVED_PROJECT_FILES


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: str,
    request: Request,
    format: Optional[str] = None,
    path: str = "",
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """List files in a project directory with extension-based viewer resolution."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        entries = directory_service.list_files(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found") from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is not a directory") from exc

    current_path = path.strip("/")
    parent_path = ""
    if current_path:
        parts = current_path.split("/")
        parent_path = "/".join(parts[:-1])

    rows = []
    viewer_cache: dict[str, Optional[dict]] = {}
    for entry in entries:
        extension_key = entry.extension.lower().lstrip(".")
        if extension_key not in viewer_cache:
            viewer_cache[extension_key] = await _resolve_viewer_info(
                request,
                extension_key,
                refresh_if_missing=True,
            )
        viewer = viewer_cache[extension_key]
        rows.append(
            {
                "name": entry.name,
                "relative_path": entry.relative_path,
                "is_dir": entry.is_dir,
                "size_bytes": entry.size_bytes,
                "size": _format_size(entry.size_bytes),
                "extension": entry.extension,
                "is_editable": (not entry.is_dir and _is_editable_extension(entry.extension)),
                "viewer": viewer,
            }
        )

    if format == "html":
        controls = []
        if current_path:
            controls.append(
                f'<button class="btn btn-sm btn-secondary" hx-get="/api/v1/projects/{project_id}/files?format=html&path={parent_path}" hx-target="#project-files-browser" hx-swap="innerHTML">← Up</button>'
            )

        lines = []
        for row in rows:
            icon = "📁" if row["is_dir"] else "📄"
            if row["is_dir"]:
                action_html = (
                    f'<button class="btn btn-sm btn-secondary" '
                    f'hx-get="/api/v1/projects/{project_id}/files?format=html&path={row["relative_path"]}" '
                    f'hx-target="#project-files-browser" hx-swap="innerHTML" title="Open folder">📂</button>'
                )
            else:
                encoded_path = quote_plus(row["relative_path"])
                action_html = (
                    f'<div style="display: flex; gap: var(--spacing-xs); justify-content: flex-end;">'
                    f'<button class="btn btn-sm btn-primary" '
                    f'hx-get="/api/v1/projects/{project_id}/files/preview?format=html&path={row["relative_path"]}" '
                    f'hx-target="#project-file-preview" hx-swap="innerHTML" title="Preview file">👁</button>'
                    f'<a class="btn btn-sm btn-secondary" href="/api/v1/projects/{project_id}/files/download?path={encoded_path}" title="Download file">⬇</a>'
                    f'</div>'
                )

            viewer_name = row["viewer"]["name"] if row["viewer"] else "Fallback"
            lines.append(
                f"""
                <tr style="border-bottom: 1px solid var(--border-color);">
                    <td style="padding: var(--spacing-sm);">{icon} {html.escape(row['name'])}</td>
                    <td style="padding: var(--spacing-sm); color: var(--text-secondary);">{html.escape(row['extension'] or '-')}</td>
                    <td style="padding: var(--spacing-sm); color: var(--text-secondary);">{html.escape(row['size']) if not row['is_dir'] else '-'}</td>
                    <td style="padding: var(--spacing-sm); color: var(--text-secondary);">{html.escape(viewer_name)}</td>
                    <td style="padding: var(--spacing-sm); text-align: right;">{action_html}</td>
                </tr>
                """
            )

        controls_html = "".join(controls) or ""
        empty_html = ""
        if not lines:
            empty_html = (
                '<p style="margin: 0; color: var(--text-secondary); padding: var(--spacing-md) 0;">No files found in this directory.</p>'
            )

        return HTMLResponse(
            f"""
            <div style="display: grid; gap: var(--spacing-md);">
                <div style="display: flex; justify-content: space-between; align-items: center; gap: var(--spacing-md);">
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem;">Path: /{html.escape(current_path) if current_path else ''}</p>
                    <div style="display: flex; gap: var(--spacing-sm);">{controls_html}</div>
                </div>
                {empty_html}
                <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
                    <thead style="border-bottom: 1px solid var(--border-color);">
                        <tr>
                            <th style="padding: var(--spacing-sm); text-align: left;">Name</th>
                            <th style="padding: var(--spacing-sm); text-align: left;">Type</th>
                            <th style="padding: var(--spacing-sm); text-align: left;">Size</th>
                            <th style="padding: var(--spacing-sm); text-align: left;">Viewer</th>
                            <th style="padding: var(--spacing-sm); text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(lines)}
                    </tbody>
                </table>
            </div>
            """
        )

    return {
        "project_id": project_id,
        "path": current_path,
        "parent_path": parent_path,
        "items": rows,
    }


@router.get("/{project_id}/files/content")
async def get_project_file_content(
    project_id: str,
    path: str,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Return editable text file content for the project file editor."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    extension = os.path.splitext(path)[1].lstrip(".").lower()
    if not _is_editable_extension(extension):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type is not editable")

    try:
        content = directory_service.read_file(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    except IsADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is a directory") from exc

    if len(content) > MAX_TEXT_EDITOR_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds editor size limit of {MAX_TEXT_EDITOR_FILE_SIZE} bytes",
        )

    return {
        "project_id": project_id,
        "path": path,
        "extension": extension,
        "is_markdown": extension in {"md", "markdown"},
        "size_bytes": len(content),
        "content": content.decode("utf-8", errors="replace"),
    }


@router.put("/{project_id}/files/content")
async def update_project_file_content(
    project_id: str,
    payload: UpdateProjectFileContentRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """Persist text file editor changes to the project filesystem."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    extension = os.path.splitext(payload.path)[1].lstrip(".").lower()
    if not _is_editable_extension(extension):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File type is not editable")

    content_bytes = payload.content.encode("utf-8")
    if len(content_bytes) > MAX_TEXT_EDITOR_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds editor size limit of {MAX_TEXT_EDITOR_FILE_SIZE} bytes",
        )

    try:
        directory_service.write_file(payload.path, content_bytes, create_parents=False)
    except UnsafeFilenameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc

    updated_tags: list[str] | None = None
    if _is_project_info_path(payload.path):
        service = ProjectService(session)
        updated_tags = service.refresh_project_tags_cache(project_id)

    response_payload = {
        "project_id": project_id,
        "path": payload.path,
        "size_bytes": len(content_bytes),
        "size": _format_size(len(content_bytes)),
    }
    if updated_tags is not None:
        response_payload["tags"] = updated_tags

    return response_payload


@router.post("/{project_id}/files/markdown-preview")
async def preview_project_markdown_content(
    project_id: str,
    payload: MarkdownPreviewRequest,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Render markdown editor content to safe HTML for live previews."""
    _resolve_project_for_owner(project_id, current_user_id, session)
    return {"html": render_markdown(payload.content or "")}


@router.get("/{project_id}/files/summary")
async def get_project_files_summary(
    project_id: str,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Return filesystem-backed project summary stats for the detail page cards."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    created_at = project.created_at
    if created_at is not None and hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()

    root = Path(directory_service._root)
    directory_exists = root.is_dir()

    total_size_bytes = 0
    file_count = 0
    directory_count = 0
    model_file_count = 0

    if directory_exists:
        for item in root.rglob("*"):
            try:
                relative = item.relative_to(root)
            except ValueError:
                continue

            if any(part.startswith(".") for part in relative.parts):
                continue

            if item.is_dir():
                directory_count += 1
                continue

            if item.is_file() and not item.is_symlink():
                file_count += 1
                total_size_bytes += item.stat().st_size
                if relative.parts and relative.parts[0] == "models":
                    model_file_count += 1

    return {
        "project_id": project_id,
        "created_at": created_at,
        "file_count": file_count,
        "directory_count": directory_count,
        "model_file_count": model_file_count,
        "total_size_bytes": total_size_bytes,
        "total_size": _format_size(total_size_bytes),
        "storage": {
            "directory_path": str(root),
            "directory_exists": directory_exists,
            "project_info_exists": (root / "ProjectInfo.md").is_file(),
            "print_history_exists": (root / "PrintHistory.md").is_file(),
        },
    }


@router.post("/{project_id}/files/upload", status_code=status.HTTP_201_CREATED)
async def upload_project_file(
    project_id: str,
    file: UploadFile = File(...),
    path: str = Form(""),
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """Upload a file into a project directory path (root by default)."""
    if not file or not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file provided")

    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    target_path = path.strip("/")
    if target_path:
        try:
            directory_service.list_files(target_path)
        except PathTraversalError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except PathNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found") from exc
        except NotADirectoryError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is not a directory") from exc

    content = await file.read()
    if len(content) > MAX_PROJECT_FILE_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_PROJECT_FILE_UPLOAD_SIZE} bytes",
        )

    try:
        safe_name = directory_service.sanitize_filename(file.filename)
        relative_path = f"{target_path}/{safe_name}" if target_path else safe_name
        directory_service.write_file(relative_path, content, create_parents=False)
    except UnsafeFilenameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found") from exc

    return {
        "project_id": project_id,
        "path": target_path,
        "relative_path": relative_path,
        "name": safe_name,
        "size_bytes": len(content),
        "size": _format_size(len(content)),
    }


@router.post("/{project_id}/files/create", status_code=status.HTTP_201_CREATED)
async def create_project_file(
    project_id: str,
    payload: CreateProjectFileRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """Create a new file in a project directory from supported type templates."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    target_path = payload.path.strip("/")
    if target_path:
        try:
            entries = directory_service.list_files(target_path)
        except PathTraversalError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except PathNotFoundError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found") from exc
        except NotADirectoryError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is not a directory") from exc
    else:
        entries = directory_service.list_files("")

    file_type = _normalize_file_type(payload.file_type)
    if file_type not in CREATEABLE_FILE_TEMPLATES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported file type")

    requested_name = payload.name.strip()
    if not requested_name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required")

    safe_name = directory_service.sanitize_filename(requested_name)
    if "." in safe_name:
        ext = safe_name.rsplit(".", 1)[-1].lower()
        if ext != file_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File extension '.{ext}' does not match requested type '.{file_type}'",
            )
        final_name = safe_name
    else:
        final_name = f"{safe_name}.{file_type}"

    existing_names = {entry.name.lower() for entry in entries}
    if final_name.lower() in existing_names:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File already exists")

    content_text = CREATEABLE_FILE_TEMPLATES[file_type]
    content = content_text.encode("utf-8")
    relative_path = f"{target_path}/{final_name}" if target_path else final_name

    try:
        directory_service.write_file(relative_path, content, create_parents=False)
    except UnsafeFilenameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found") from exc

    return {
        "project_id": project_id,
        "path": target_path,
        "relative_path": relative_path,
        "name": final_name,
        "extension": file_type,
        "size_bytes": len(content),
        "size": _format_size(len(content)),
    }

@router.post("/{project_id}/files/create-folder", status_code=status.HTTP_201_CREATED)
async def create_project_folder(
    project_id: str,
    payload: CreateProjectFolderRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """Create a new folder in the selected project directory path."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        relative_path = directory_service.create_directory(payload.path.strip("/"), payload.name)
    except UnsafeFilenameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Directory not found") from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is not a directory") from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Folder already exists") from exc

    return {
        "project_id": project_id,
        "path": payload.path.strip("/"),
        "relative_path": relative_path,
        "name": Path(relative_path).name,
    }


@router.post("/{project_id}/files/rename")
async def rename_project_path(
    project_id: str,
    payload: RenameProjectPathRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """Rename a file or directory path within a project."""
    source_path = payload.path.strip("/")
    if _is_reserved_project_file_path(source_path):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reserved project files cannot be renamed")

    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        renamed_path = directory_service.rename_path(source_path, payload.new_name)
    except UnsafeFilenameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File or directory not found") from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Target name already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": project_id,
        "old_path": source_path,
        "new_path": renamed_path,
        "name": Path(renamed_path).name,
    }


@router.post("/{project_id}/files/move")
async def move_project_paths(
    project_id: str,
    payload: MoveProjectPathsRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
):
    """Move one or more files/directories into a destination folder."""
    source_paths = [item.strip("/") for item in payload.paths if item and item.strip("/")]
    if not source_paths:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one path is required")
    if any(_is_reserved_project_file_path(path) for path in source_paths):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reserved project files cannot be moved")

    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        moved_paths = directory_service.move_paths(source_paths, payload.destination_path.strip("/"))
    except UnsafeFilenameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File or directory not found") from exc
    except NotADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Destination is not a directory") from exc
    except FileExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A destination file/folder already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return {
        "project_id": project_id,
        "destination_path": payload.destination_path.strip("/"),
        "moved_count": len(moved_paths),
        "moved_paths": moved_paths,
    }


@router.get("/{project_id}/files/preview")
async def preview_project_file(
    project_id: str,
    request: Request,
    path: str,
    format: Optional[str] = None,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Preview a project file and indicate which viewer hook is selected."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        content = directory_service.read_file(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    except IsADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is a directory") from exc

    extension = os.path.splitext(path)[1].lstrip(".").lower()
    viewer = await _resolve_viewer_info(request, extension, refresh_if_missing=True)

    preview_text = None
    preview_mode = "binary"
    if extension in {"md", "txt", "log", "yaml", "yml", "json", "gcode", "csv", "py"}:
        preview_mode = "text"
        preview_text = content.decode("utf-8", errors="replace")[:20000]

    payload = {
        "path": path,
        "extension": extension,
        "size_bytes": len(content),
        "viewer": viewer,
        "preview_mode": preview_mode,
        "preview_text": preview_text,
    }

    if format == "html":
        viewer_header = "No viewer plugin enabled for this extension"
        viewer_details = "Using core fallback preview."
        if viewer:
            viewer_header = f"Viewer hook: {viewer['name']}"
            viewer_details = (
                f"Plugin {viewer['plugin_id']} matched extension '.{extension}'. "
                "Rendering through plugin-provided viewer script."
            )
        viewer_tooltip = html.escape(f"{viewer_header} {viewer_details}")

        if viewer and viewer.get("has_js"):
            preview_token = uuid.uuid4().hex
            plugin_context = {
                "containerId": "project-plugin-viewer",
                "projectId": project_id,
                "filePath": path,
                "extension": extension,
                "fileUrl": f"/api/v1/projects/{project_id}/files/raw?path={quote_plus(path)}",
            }
            context_json = html.escape(json.dumps(plugin_context), quote=False)
            viewer_script_url = (
                f"/api/v1/projects/{project_id}/files/viewer-script?viewer_id={quote_plus(str(viewer['viewer_id']))}&preview_token={preview_token}"
            )
            body_html = f"""
            <div id="project-plugin-viewer" style="height: 420px; border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-secondary); overflow: hidden; display: grid; place-items: center; color: var(--text-secondary);">
                Loading viewer...
            </div>
            <script id="project-plugin-viewer-context" type="application/json">{context_json}</script>
            <script>
                (function () {{
                    const container = document.getElementById('project-plugin-viewer');
                    import('{viewer_script_url}')
                        .catch(function (error) {{
                            if (container) {{
                                container.innerHTML = '<p style="margin:0;padding:1rem;color:#fca5a5;">Viewer failed to load: ' + String(error) + '</p>';
                            }}
                        }});
                }})();
            </script>
            """
        elif preview_mode == "text":
            body_html = (
                f'<pre style="margin: 0; max-height: 420px; overflow: auto; padding: var(--spacing-md); background: var(--bg-secondary); border: 1px solid var(--border-color); border-radius: 4px;">{html.escape(preview_text or "")}</pre>'
            )
        else:
            body_html = '<p style="margin: 0; color: var(--text-secondary);">Binary preview is not rendered in v1. Use a viewer plugin for this file type.</p>'

        return HTMLResponse(
            f"""
            <div style="display: grid; gap: var(--spacing-md);">
                <div>
                    <h4 style="margin: 0;">{html.escape(os.path.basename(path))}</h4>
                    <p style="margin: var(--spacing-xs) 0 0 0; color: var(--text-secondary); font-size: 0.875rem;">{html.escape(path)} · {_format_size(len(content))}</p>
                </div>
                <div style="display: flex; align-items: center; gap: var(--spacing-sm); padding: var(--spacing-sm) var(--spacing-md); border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-secondary);">
                    <p style="margin: 0; font-weight: 600;">{html.escape(viewer_header)}</p>
                    <span title="{viewer_tooltip}" style="display: inline-flex; width: 1.25rem; height: 1.25rem; align-items: center; justify-content: center; border: 1px solid var(--border-color); border-radius: 999px; cursor: help; color: var(--text-secondary); font-size: 0.8rem;">i</span>
                </div>
                {body_html}
            </div>
            """
        )

    return payload


@router.get("/{project_id}/files/viewer-script")
async def get_project_file_viewer_script(
    project_id: str,
    viewer_id: str,
    request: Request,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Serve the JavaScript module for an enabled viewer contribution."""
    _resolve_project_for_owner(project_id, current_user_id, session)
    manager = getattr(request.app.state, "plugin_manager", None)
    if manager is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plugin manager unavailable")

    viewer = manager.viewers.get(viewer_id)
    if viewer is None or viewer.js_file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Viewer script not found")

    return FileResponse(viewer.js_file, media_type="text/javascript")


@router.get("/{project_id}/files/raw")
async def get_project_file_raw(
    project_id: str,
    path: str,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Return raw file bytes with an inferred media type for in-browser viewers."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        content = directory_service.read_file(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    except IsADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is a directory") from exc

    return Response(content=content, media_type=_guess_raw_media_type(path))


@router.get("/{project_id}/files/download")
async def download_project_file(
    project_id: str,
    path: str,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
):
    """Download a file from the project filesystem."""
    project = _resolve_project_for_owner(project_id, current_user_id, session)
    directory_service = service_for_project_owner(
        session,
        project.owner_id,
        project.slug,
        legacy_segment=project.category,
    )

    try:
        content = directory_service.read_file(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found") from exc
    except IsADirectoryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path is a directory") from exc

    filename = os.path.basename(path) or "download.bin"
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
            requested_visibility = body.get("visibility")
            
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
                if requested_visibility:
                    requested_visibility = sanitize_text_input(str(requested_visibility), "Project visibility")
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

            if requested_visibility and requested_visibility not in {"private", "public"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Visibility must be either 'private' or 'public'",
                )
            if isinstance(metadata, dict) and requested_visibility:
                metadata["visibility"] = requested_visibility
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
        category = metadata.get("category", "Uncategorized") if isinstance(metadata, dict) else "Uncategorized"
        resolved_visibility = metadata.get("visibility", "private") if isinstance(metadata, dict) else "private"
        if resolved_visibility not in {"private", "public"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Visibility must be either 'private' or 'public'",
            )
        project_dto = service.create_project(
            owner_id=current_user_id,
            title=title,
            category=category,
            visibility=resolved_visibility,
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
    projects = service.list_accessible_projects(user_id=current_user_id, skip=skip, limit=limit)

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


@router.get("/public", response_model=ProjectListResponse)
async def list_public_projects(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_db),
) -> ProjectListResponse:
    """List publicly visible projects without authentication."""
    limit = min(limit, 1000)
    if limit < 0 or skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skip and limit must be >= 0",
        )

    public_projects = session.execute(
        select(Project)
        .where(Project.visibility == "public")
        .where(Project.is_archived == False)
        .offset(skip)
        .limit(limit)
    ).scalars().all()

    service = ProjectService(session)
    items = [service._to_dto(project) for project in public_projects]
    return ProjectListResponse(
        items=[ProjectResponse(**p.__dict__) for p in items],
        total=len(items),
        skip=skip,
        limit=limit,
    )


@router.get("/public/{project_id}", response_model=ProjectResponse)
async def get_public_project(
    project_id: str,
    session: Session = Depends(get_db),
) -> ProjectResponse:
    """Read a publicly visible project without authentication."""
    project = _resolve_project_model(project_id, session)
    if project.visibility != "public" or project.is_archived:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    dto = ProjectService(session)._to_dto(project)
    return ProjectResponse(**dto.__dict__)


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

    access_service = ProjectAccessService(session)
    project_model = _resolve_project_model(project_id, session)

    if not access_service.can_view(project_model, current_user_id):
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
            requested_category = request.custom_metadata.get("category")
            if requested_category:
                sanitized_category = sanitize_text_input(str(requested_category), "Project category")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    requested_visibility = None
    if request.custom_metadata and request.custom_metadata.get("visibility") is not None:
        raw_visibility = str(request.custom_metadata.get("visibility"))
        requested_visibility = sanitize_text_input(raw_visibility, "Project visibility")
        if requested_visibility not in {"private", "public"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Visibility must be either 'private' or 'public'",
            )

    try:
        updated = service.update_project(
            project_id=project_id,
            title=sanitized_title,
            category=sanitized_category,
            visibility=requested_visibility,
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
        sanitized_visibility = sanitize_text_input(visibility, "Project visibility") if visibility else None
        if sanitized_visibility and sanitized_visibility not in {"private", "public"}:
            raise ValueError("Visibility must be either 'private' or 'public'")

        service.update_project(
            project_id=project_id,
            title=sanitized_name,
            visibility=sanitized_visibility,
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


@router.get("/{project_id}/collaborators", response_model=list[CollaboratorResponse])
async def list_project_collaborators(
    project_id: str,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
) -> list[CollaboratorResponse]:
    """List collaborators for a project (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage collaborators",
        )

    access_service = ProjectAccessService(session)
    collaborators = access_service.list_collaborators(project_id)
    return [
        CollaboratorResponse(
            user_id=item.user_id,
            role=item.role,
            granted_by_id=item.granted_by_id,
            created_at=item.created_at,
        )
        for item in collaborators
    ]


@router.post("/{project_id}/collaborators", response_model=CollaboratorResponse)
async def upsert_project_collaborator(
    project_id: str,
    request: CollaboratorRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> CollaboratorResponse:
    """Add or update a collaborator role (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage collaborators",
        )
    if request.user_id == current_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner role is implicit and cannot be assigned",
        )

    user = session.execute(select(User).where(User.id == request.user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    access_service = ProjectAccessService(session)
    collaborator = access_service.upsert_collaborator(
        project=project,
        target_user_id=request.user_id,
        role=request.role,
        granted_by_id=current_user_id,
    )
    return CollaboratorResponse(
        user_id=collaborator.user_id,
        role=collaborator.role,
        granted_by_id=collaborator.granted_by_id,
        created_at=collaborator.created_at,
    )


@router.delete("/{project_id}/collaborators/{user_id}")
async def remove_project_collaborator(
    project_id: str,
    user_id: str,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> Response:
    """Remove a collaborator from a project (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage collaborators",
        )

    access_service = ProjectAccessService(session)
    removed = access_service.remove_collaborator(project_id=project_id, target_user_id=user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{project_id}/invitations", response_model=InvitationResponse)
async def create_project_invitation(
    project_id: str,
    request: InvitationRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> InvitationResponse:
    """Create an invitation token for project access (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to invite collaborators",
        )

    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    access_service = ProjectAccessService(session)
    invitation = access_service.create_invitation(
        project=project,
        invited_email=request.email,
        role=request.role,
        token_hash=token_hash,
        expires_at=expires_at,
        invited_by_id=current_user_id,
    )

    inviter_name = session.execute(select(User).where(User.id == current_user_id)).scalar_one().display_name
    try:
        send_project_invitation_email(
            session=session,
            invitation=invitation,
            project=project,
            token=token,
            inviter_name=str(inviter_name),
        )
    except EmailDeliveryError as exc:
        access_service.revoke_invitation(invitation.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Invitation email delivery failed: {exc}",
        ) from exc

    return InvitationResponse(
        invitation_id=invitation.id,
        invited_email=invitation.invited_email,
        role=invitation.role,
        expires_at=invitation.expires_at,
        token=token,
    )


@router.post("/invitations/{token}/accept", response_model=CollaboratorResponse)
async def accept_project_invitation(
    token: str,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> CollaboratorResponse:
    """Accept an invitation token and become a collaborator."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    access_service = ProjectAccessService(session)
    collaborator = access_service.accept_invitation(token_hash=token_hash, user_id=current_user_id)
    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid, expired, revoked, or already accepted",
        )

    return CollaboratorResponse(
        user_id=collaborator.user_id,
        role=collaborator.role,
        granted_by_id=collaborator.granted_by_id,
        created_at=collaborator.created_at,
    )


@router.get("/invitations/mine", response_model=list[PendingInvitationResponse])
async def list_my_pending_invitations(
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
) -> list[PendingInvitationResponse]:
    """List pending invitations for the authenticated user."""
    access_service = ProjectAccessService(session)
    invitations = access_service.list_pending_invitations_for_user(current_user_id)

    results: list[PendingInvitationResponse] = []
    for invitation in invitations:
        project = session.execute(
            select(Project).where(Project.id == invitation.project_id)
        ).scalar_one_or_none()
        if not project:
            continue
        results.append(
            PendingInvitationResponse(
                invitation_id=invitation.id,
                project_id=project.id,
                project_title=project.title,
                invited_email=invitation.invited_email,
                role=invitation.role,
                expires_at=invitation.expires_at,
                created_at=invitation.created_at,
            )
        )
    return results


@router.post("/invitations/id/{invitation_id}/accept", response_model=CollaboratorResponse)
async def accept_project_invitation_by_id(
    invitation_id: str,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> CollaboratorResponse:
    """Accept a pending invitation by invitation id for the authenticated user."""
    access_service = ProjectAccessService(session)
    collaborator = access_service.accept_invitation_by_id(
        invitation_id=invitation_id,
        user_id=current_user_id,
    )
    if not collaborator:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid, expired, revoked, already accepted, or does not match your account",
        )

    return CollaboratorResponse(
        user_id=collaborator.user_id,
        role=collaborator.role,
        granted_by_id=collaborator.granted_by_id,
        created_at=collaborator.created_at,
    )


@router.get("/{project_id}/invitations", response_model=list[InvitationSummaryResponse])
async def list_project_invitations(
    project_id: str,
    include_inactive: bool = False,
    current_user_id: str = Depends(require_scopes(["read:projects"])),
    session: Session = Depends(get_db),
) -> list[InvitationSummaryResponse]:
    """List project invitations (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage invitations",
        )

    access_service = ProjectAccessService(session)
    invitations = access_service.list_invitations(
        project_id=project_id,
        include_inactive=include_inactive,
    )
    return [
        InvitationSummaryResponse(
            invitation_id=item.id,
            invited_email=item.invited_email,
            role=item.role,
            expires_at=item.expires_at,
            accepted_at=item.accepted_at,
            revoked_at=item.revoked_at,
            created_at=item.created_at,
        )
        for item in invitations
    ]


@router.patch("/{project_id}/invitations/{invitation_id}", response_model=InvitationSummaryResponse)
async def update_project_invitation(
    project_id: str,
    invitation_id: str,
    request: InvitationUpdateRequest,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> InvitationSummaryResponse:
    """Update role for a pending invitation (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage invitations",
        )

    invitation = session.execute(
        select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
    ).scalar_one_or_none()
    if not invitation or invitation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    access_service = ProjectAccessService(session)
    updated = access_service.update_invitation_role(invitation_id=invitation_id, role=request.role)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation cannot be updated",
        )

    return InvitationSummaryResponse(
        invitation_id=updated.id,
        invited_email=updated.invited_email,
        role=updated.role,
        expires_at=updated.expires_at,
        accepted_at=updated.accepted_at,
        revoked_at=updated.revoked_at,
        created_at=updated.created_at,
    )


@router.delete("/{project_id}/invitations/{invitation_id}")
async def revoke_project_invitation(
    project_id: str,
    invitation_id: str,
    current_user_id: str = Depends(require_scopes(["write:projects"])),
    session: Session = Depends(get_db),
) -> Response:
    """Revoke a pending invitation (owner only)."""
    project = _resolve_project_model(project_id, session)
    if project.owner_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to manage invitations",
        )

    invitation = session.execute(
        select(ProjectInvitation).where(ProjectInvitation.id == invitation_id)
    ).scalar_one_or_none()
    if not invitation or invitation.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    access_service = ProjectAccessService(session)
    access_service.revoke_invitation(invitation_id)
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
            category="Uncategorized",
            visibility=validated.visibility,
            description=validated.description,
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
