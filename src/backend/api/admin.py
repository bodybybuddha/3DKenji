"""Admin panel API endpoints."""

import html
import json
import logging
import os
from collections import deque
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.auth import get_current_user
from backend.db import get_db
from backend.models.user import User
from sqlalchemy import select
from backend.services.user_service import UserService
from backend.plugins.auth_password import PasswordAuthProvider

logger = logging.getLogger(__name__)

# Initialize templates for HTML responses
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="/admin", tags=["admin"])

LOG_LINE_LIMIT = 200


def _get_log_file_path() -> Path:
    log_file = os.getenv("LOG_FILE", "data/logs/app.log")
    log_path = Path(log_file)
    if log_path.is_absolute():
        return log_path

    base_dir = Path(__file__).resolve().parents[3]
    return base_dir / log_path


def _read_log_lines(path: Path, limit: int = LOG_LINE_LIMIT) -> list[str]:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as log_file:
            return list(deque(log_file, maxlen=limit))
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.warning("Failed to read log file %s: %s", path, exc)
        return []


def _parse_log_line(line: str) -> dict[str, str]:
    raw_line = line.strip()
    if not raw_line:
        return {
            "timestamp": "",
            "level": "INFO",
            "module": "",
            "message": "",
        }

    try:
        record = json.loads(raw_line)
        return {
            "timestamp": str(record.get("timestamp", "")),
            "level": str(record.get("level", "INFO")),
            "module": str(record.get("module", record.get("logger", ""))),
            "message": str(record.get("message", "")),
        }
    except json.JSONDecodeError:
        return {
            "timestamp": "",
            "level": "INFO",
            "module": "",
            "message": raw_line,
        }


# Request Models
class AdminSettingsRequest(BaseModel):
    """Request to update admin settings."""
    api_title: Optional[str] = None
    api_version: Optional[str] = None
    max_upload_mb: Optional[int] = None


# Response Models
class StatsResponse(BaseModel):
    """Admin statistics response."""
    total_users: int
    total_projects: int
    total_models: int
    total_storage_bytes: int
    api_status: str
    db_status: str
    storage_status: str


class HealthResponse(BaseModel):
    """System health status response."""
    api_healthy: bool
    db_healthy: bool
    storage_healthy: bool
    memory_usage_percent: float
    cpu_usage_percent: float
    timestamp: str


# Admin authentication dependency
async def require_admin(
    current_user_id: str = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> str:
    """Verify user is admin and active."""
    user = session.execute(
        select(User).where(User.id == current_user_id)
    ).scalar_one_or_none()

    if not user or not user.is_active:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not active",
        )

    if not user.is_admin:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user_id


# Stats endpoints
@router.get("/stats", response_model=StatsResponse)
async def get_admin_stats(
    format: Optional[str] = None,
    request: Request = None,
    admin_user: str = Depends(require_admin),
) -> StatsResponse:
    """
    Get admin statistics.
    
    Returns system-wide statistics like user count, project count, etc.
    Supports HTML format via ?format=html for dashboard display.
    """
    stats = StatsResponse(
        total_users=42,  # TODO: Query from database
        total_projects=128,  # TODO: Query from database
        total_models=356,  # TODO: Query from database
        total_storage_bytes=1024 * 1024 * 512,  # 512 MB TODO: Calculate from storage
        api_status="healthy",
        db_status="healthy",
        storage_status="healthy",
    )
    
    if format == "html":
        # Return JSON suitable for chart rendering in JavaScript
        return JSONResponse({
            "stats": stats.model_dump(),
            "timestamp": datetime.utcnow().isoformat(),
        })
    
    return stats


@router.get("/health", response_class=HTMLResponse)
async def get_admin_health(
    request: Request,
    format: Optional[str] = None,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get system health status as HTML."""
    health = HealthResponse(
        api_healthy=True,
        db_healthy=True,
        storage_healthy=True,
        memory_usage_percent=45.2,
        cpu_usage_percent=32.1,
        timestamp=datetime.utcnow().isoformat(),
    )
    
    # Calculate uptime
    start_time = getattr(request.app.state, 'start_time', datetime.now())
    uptime = datetime.now() - start_time
    days = uptime.days
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    uptime_str = f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    
    return f"""
    <div style="padding: var(--spacing-lg);">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-lg); margin-bottom: var(--spacing-lg);">
            <div>
                <h4>API Status</h4>
                <p style="margin: 0; font-size: 1.25rem;">{'✅ Healthy' if health.api_healthy else '❌ Down'}</p>
            </div>
            <div>
                <h4>Database Status</h4>
                <p style="margin: 0; font-size: 1.25rem;">{'✅ Healthy' if health.db_healthy else '❌ Down'}</p>
            </div>
            <div>
                <h4>Storage Status</h4>
                <p style="margin: 0; font-size: 1.25rem;">{'✅ Healthy' if health.storage_healthy else '❌ Down'}</p>
            </div>
            <div>
                <h4>Uptime</h4>
                <p style="margin: 0; font-size: 1.25rem;">{uptime_str}</p>
            </div>
        </div>
        
        <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px;">
            <h4>Resource Usage</h4>
            <div style="display: grid; gap: var(--spacing-md);">
                <div>
                    <label>Memory Usage</label>
                    <div style="background: var(--border-color); border-radius: 4px; overflow: hidden; height: 20px;">
                        <div style="background: var(--primary); width: {health.memory_usage_percent}%; height: 100%;"></div>
                    </div>
                    <small>{health.memory_usage_percent:.1f}%</small>
                </div>
                <div>
                    <label>CPU Usage</label>
                    <div style="background: var(--border-color); border-radius: 4px; overflow: hidden; height: 20px;">
                        <div style="background: var(--warning); width: {health.cpu_usage_percent}%; height: 100%;"></div>
                    </div>
                    <small>{health.cpu_usage_percent:.1f}%</small>
                </div>
            </div>
        </div>
    </div>
    """


@router.get("/metrics", response_class=HTMLResponse)
async def get_admin_metrics(
    request: Request,
    format: Optional[str] = None,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get performance metrics as HTML."""
    return """
    <div style="padding: var(--spacing-lg); border-bottom: 1px solid var(--border-color);">
        <h3>Performance Metrics</h3>
    </div>
    <div style="padding: var(--spacing-lg);">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">Requests/sec</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">234</div>
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">Avg Response Time</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">45ms</div>
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">Error Rate</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">0.2%</div>
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">DB Query Time</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">12ms</div>
            </div>
        </div>
    </div>
    """


# Users management endpoints
@router.get("/users", response_class=HTMLResponse)
async def get_admin_users_list(
    format: Optional[str] = None,
    request: Request = None,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get list of all users as HTML table."""
    users = [
        {"id": "1", "username": "admin", "email": "admin@example.com", "role": "admin", "created_at": "2026-01-01"},
        {"id": "2", "username": "user1", "email": "user1@example.com", "role": "user", "created_at": "2026-01-15"},
    ]
    
    return f"""
    <table style="width: 100%; border-collapse: collapse;">
        <thead style="border-bottom: 2px solid var(--border-color);">
            <tr>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Username</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Email</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Role</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Joined</th>
                <th style="padding: var(--spacing-md); text-align: right; font-weight: 600;">Action</th>
            </tr>
        </thead>
        <tbody>
            {"".join(f'''
            <tr>
                <td style="padding: var(--spacing-md);">{user["username"]}</td>
                <td style="padding: var(--spacing-md);">{user["email"]}</td>
                <td style="padding: var(--spacing-md);">
                    <span style="background: var(--primary); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                        {user["role"]}
                    </span>
                </td>
                <td style="padding: var(--spacing-md); color: var(--text-secondary); font-size: 0.875rem;">{user["created_at"]}</td>
                <td style="padding: var(--spacing-md); text-align: right;">
                    <button class="btn btn-sm btn-secondary" hx-get="/api/v1/admin/users/{user["id"]}/edit-modal" hx-target="body" hx-swap="beforeend">
                        Edit
                    </button>
                </td>
            </tr>
            ''' for user in users)}
        </tbody>
    </table>
    """


# Plugins management endpoints
@router.get("/plugins", response_class=HTMLResponse)
async def get_admin_plugins_list(
    format: Optional[str] = None,
    request: Request = None,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get list of all plugins as HTML."""
    plugins = [
        {"id": "dark-theme", "name": "Dark Theme", "version": "1.0.0", "status": "enabled"},
        {"id": "light-theme", "name": "Light Theme", "version": "1.0.0", "status": "enabled"},
    ]
    
    return f"""
    <div style="display: grid; gap: var(--spacing-lg);">
        {"".join(f'''
        <div style="padding: var(--spacing-lg); border: 1px solid var(--border-color); border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0 0 var(--spacing-xs) 0;">{plugin["name"]}</h4>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem;">Version {plugin["version"]}</p>
                </div>
                <div style="display: flex; gap: var(--spacing-sm);">
                    <span style="background: {'var(--success)' if plugin["status"] == 'enabled' else 'var(--warning)'}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 0.75rem;">
                        {plugin["status"]}
                    </span>
                    <button class="btn btn-sm btn-secondary">Settings</button>
                </div>
            </div>
        </div>
        ''' for plugin in plugins)}
    </div>
    """


# Logs endpoints
@router.get("/logs", response_class=HTMLResponse)
async def get_admin_logs(
    level: Optional[str] = None,
    request: Request = None,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get system logs as HTML."""
    log_path = _get_log_file_path()
    raw_lines = _read_log_lines(log_path)
    logs = [_parse_log_line(line) for line in raw_lines]

    if level:
        logs = [log for log in logs if log["level"].lower() == level.lower()]

    logs = list(reversed([log for log in logs if log["message"]]))

    if not logs:
        return """
        <div style="padding: var(--spacing-lg); text-align: center;">
            <p style="color: var(--text-secondary); margin: 0;">No logs available.</p>
        </div>
        """
    
    return f"""
    <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem;">
        <thead style="border-bottom: 1px solid var(--border-color);">
            <tr>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Timestamp</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Level</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Module</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Message</th>
            </tr>
        </thead>
        <tbody>
            {"".join(f'''
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: var(--spacing-sm);">{html.escape(log["timestamp"])}</td>
                <td style="padding: var(--spacing-sm);">
                    <span style="background: var(--bg-secondary); padding: 2px 6px; border-radius: 3px;">
                        {html.escape(log["level"])}</span>
                </td>
                <td style="padding: var(--spacing-sm); color: var(--text-secondary);">{html.escape(log["module"])}</td>
                <td style="padding: var(--spacing-sm);">{html.escape(log["message"])}</td>
            </tr>
            ''' for log in logs)}
        </tbody>
    </table>
    """


# Settings endpoints
@router.post("/settings/api")
async def update_api_settings(
    request: AdminSettingsRequest,
    admin_user: str = Depends(require_admin),
):
    """Update API settings."""
    # TODO: Save to database/config
    return {"message": "Settings updated", "settings": request.model_dump()}


@router.post("/settings/storage")
async def update_storage_settings(
    request: AdminSettingsRequest,
    admin_user: str = Depends(require_admin),
):
    """Update storage settings."""
    # TODO: Save to database/config
    return {"message": "Settings updated", "settings": request.model_dump()}


# Clear logs endpoint
@router.post("/logs/clear")
async def clear_logs(
    admin_user: str = Depends(require_admin),
):
    """Clear all logs."""
    log_path = _get_log_file_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8"):
            pass
    except Exception as exc:
        logger.error("Failed to clear logs at %s: %s", log_path, exc)
        raise HTTPException(status_code=500, detail="Failed to clear logs")

    return {"message": "Logs cleared"}


# Modal endpoints for HTMX form loading
@router.get("/users/create-modal", response_class=HTMLResponse)
async def get_create_user_modal(
    request: Request,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get the create user modal form."""
    return templates.TemplateResponse("admin/users/form-modal.html", {
        "request": request,
    }).body.decode()


@router.get("/users/{user_id}/edit-modal", response_class=HTMLResponse)
async def get_edit_user_modal(
    user_id: str,
    request: Request,
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> str:
    """Get the edit user modal form."""
    # Load user from database
    user = session.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert to dict for template
    user_dict = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
    }
    
    return templates.TemplateResponse("admin/users/form-modal.html", {
        "request": request,
        "user": user_dict,
    }).body.decode()


@router.post("/users", response_class=HTMLResponse)
async def create_user(
    username: str = Form(...),
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> str:
    """Create a new user."""
    try:
        # Check if username already exists
        existing_user = session.execute(
            select(User).where(User.username == username)
        ).scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Check if email already exists
        existing_email = session.execute(
            select(User).where(User.email == email)
        ).scalar_one_or_none()
        
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        # Create user
        user_service = UserService(session)
        auth_provider = PasswordAuthProvider()
        
        # Hash password
        password_hash = auth_provider.hash_password(password)
        
        # Determine if user should be admin
        is_admin = (role == "admin")
        
        # Create user
        new_user = user_service.create_user(
            username=username,
            email=email,
            display_name=display_name,
            password_hash=password_hash,
            is_admin=is_admin,
            is_active=is_active
        )
        
        session.commit()
        
        return HTMLResponse(
            content='<div class="alert alert-success">User created successfully</div>',
            status_code=201
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")


@router.put("/users/{user_id}", response_class=HTMLResponse)
async def update_user(
    user_id: str,
    email: str = Form(...),
    display_name: str = Form(...),
    password: Optional[str] = Form(None),
    role: str = Form(...),
    is_active: bool = Form(True),
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> str:
    """Update an existing user."""
    try:
        # Load user
        user = session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Check if email is taken by another user
        if email != user.email:
            existing_email = session.execute(
                select(User).where(User.email == email, User.id != user_id)
            ).scalar_one_or_none()
            
            if existing_email:
                raise HTTPException(status_code=400, detail="Email already in use")
        
        # Update user fields
        user.email = email
        user.display_name = display_name
        user.is_admin = (role == "admin")
        user.is_active = is_active
        
        # Update password if provided
        if password:
            auth_provider = PasswordAuthProvider()
            user.password_hash = auth_provider.hash_password(password)
        
        session.commit()
        
        return HTMLResponse(
            content='<div class="alert alert-success">User updated successfully</div>',
            status_code=200
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")


@router.get("/plugins/upload-modal", response_class=HTMLResponse)
async def get_upload_plugin_modal(
    request: Request,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get the upload plugin modal form."""
    return """
    <div id="upload-plugin-modal" class="modal" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; z-index: 1000;">
      <div class="card" style="max-width: 500px; width: 90%;">
        <div style="padding: var(--spacing-lg); border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center;">
          <h2 style="margin: 0;">Upload Plugin</h2>
          <button hx-on="click: this.closest('#upload-plugin-modal').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-secondary);">
            ×
          </button>
        </div>

        <form hx-post="/api/v1/admin/plugins/upload" hx-encoding="multipart/form-data">
          <div style="padding: var(--spacing-lg); display: grid; gap: var(--spacing-md);">
            <div>
              <label>Plugin Package (ZIP)</label>
              <input type="file" name="plugin_file" accept=".zip" required class="form-control" />
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-md); border-radius: 4px;">
              <p style="font-size: 0.875rem; color: var(--text-secondary); margin: 0;">
                ℹ️ Plugins must be in a ZIP archive with plugin.json metadata file.
              </p>
            </div>
          </div>

          <div style="padding: var(--spacing-lg); border-top: 1px solid var(--border-color); display: flex; gap: var(--spacing-md); justify-content: flex-end;">
            <button type="button" class="btn btn-secondary" onclick="this.closest('#upload-plugin-modal').remove();">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary">
              Upload
            </button>
          </div>
        </form>
      </div>
    </div>
    """
