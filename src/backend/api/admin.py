"""Admin panel API endpoints."""

import html
import json
import logging
import os
from collections import deque
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from backend.api.auth import get_current_user
from backend.db import get_db
from backend.models.user import User
from backend.models.project import Project
from backend.models.model import Model
from backend.api.frontend import templates
from sqlalchemy import select, func
from backend.services.user_service import UserService
from backend.services.app_settings_service import AppSettingsService
from backend.observability import get_runtime_metrics
from backend.core.plugins import PluginManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

LOG_LINE_LIMIT = 200


def _get_plugin_manager(request: Request) -> PluginManager:
    manager = getattr(request.app.state, "plugin_manager", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Plugin manager is not initialized")
    return manager


def _get_memory_usage_percent() -> float:
    """Return system memory utilization percentage from /proc/meminfo."""
    try:
        total_kb = 0
        available_kb = 0
        with open("/proc/meminfo", "r", encoding="utf-8") as meminfo:
            for line in meminfo:
                if line.startswith("MemTotal:"):
                    total_kb = int(line.split()[1])
                elif line.startswith("MemAvailable:"):
                    available_kb = int(line.split()[1])

        if total_kb <= 0:
            return 0.0

        used_percent = ((total_kb - available_kb) / total_kb) * 100.0
        return max(0.0, min(used_percent, 100.0))
    except Exception:
        return 0.0


def _get_cpu_usage_percent() -> float:
    """Return an approximate CPU utilization based on 1-minute load average."""
    try:
        load1, _, _ = os.getloadavg()
        cpu_count = os.cpu_count() or 1
        percent = (load1 / cpu_count) * 100.0
        return max(0.0, min(percent, 100.0))
    except Exception:
        return 0.0


def _is_database_healthy(session: Session) -> bool:
    """Validate database connectivity for health status."""
    try:
        session.execute(select(1)).scalar_one_or_none()
        return True
    except Exception:
        return False


def _is_storage_healthy() -> bool:
    """Validate storage root accessibility."""
    storage_root = os.getenv("STORAGE_ROOT", "data/storage")
    try:
        os.makedirs(storage_root, exist_ok=True)
        return os.path.isdir(storage_root) and os.access(storage_root, os.R_OK | os.W_OK)
    except Exception:
        return False


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
            "username": "",
            "user_id": "",
            "client_ip": "",
        }

    try:
        record = json.loads(raw_line)
        return {
            "timestamp": str(record.get("timestamp", "")),
            "level": str(record.get("level", "INFO")),
            "module": str(record.get("module", record.get("logger", ""))),
            "message": str(record.get("message", "")),
            "username": str(record.get("username", "")),
            "user_id": str(record.get("user_id", "")),
            "client_ip": str(record.get("client_ip", "")),
        }
    except json.JSONDecodeError:
        return {
            "timestamp": "",
            "level": "INFO",
            "module": "",
            "message": raw_line,
            "username": "",
            "user_id": "",
            "client_ip": "",
        }


# Request Models
class AdminSettingsRequest(BaseModel):
    """Request to update admin settings.
    
    Attributes:
        api_title: Display name for the API shown in OpenAPI/Swagger documentation.
                   Used in API explorer and documentation headers. Default: '3DKenji API'.
        api_version: API version string displayed in OpenAPI/Swagger documentation.
                    Follows semantic versioning (e.g., '1.0.0', 'v1.0.0').
        max_upload_mb: Maximum file upload size in megabytes. Applies to model file uploads.
                      Default: 50 MB. Changes require application restart to take effect.
    """
    api_title: Optional[str] = None
    api_version: Optional[str] = None
    max_upload_mb: Optional[int] = None


class SMTPSettingsRequest(BaseModel):
    """Request to update SMTP delivery settings."""

    host: str
    port: int
    username: Optional[str] = ""
    password: Optional[str] = ""
    from_email: str
    from_name: Optional[str] = "3DKenji"
    use_starttls: bool = True
    use_tls: bool = False
    mock_delivery: bool = False


class LogSettingsRequest(BaseModel):
    """Request to update logging configuration."""

    log_level: Optional[str] = None
    max_size_mb: Optional[int] = None
    backup_count: Optional[int] = None

    @validator("log_level")
    @classmethod
    def validate_log_level(cls, v: Optional[str]) -> Optional[str]:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR"}
        if v is not None and v.upper() not in valid:
            raise ValueError(f"log_level must be one of {sorted(valid)}")
        return v.upper() if v else v

    @validator("max_size_mb")
    @classmethod
    def validate_max_size_mb(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("max_size_mb must be at least 1")
        return v

    @validator("backup_count")
    @classmethod
    def validate_backup_count(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("backup_count must be at least 1")
        return v


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
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> StatsResponse:
    """
    Get admin statistics.
    
    Returns system-wide statistics like user count, project count, etc.
    Supports HTML format via ?format=html for dashboard display.
    """
    # Query actual database values
    total_users = session.execute(
        select(func.count(User.id))
    ).scalar() or 0
    
    total_projects = session.execute(
        select(func.count(Project.id))
    ).scalar() or 0
    
    total_models = session.execute(
        select(func.count(Model.id))
    ).scalar() or 0
    
    # Sum disk_size_bytes from all projects
    total_storage_bytes = session.execute(
        select(func.sum(Project.disk_size_bytes))
    ).scalar() or 0
    
    stats = StatsResponse(
        total_users=total_users,
        total_projects=total_projects,
        total_models=total_models,
        total_storage_bytes=int(total_storage_bytes),
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
    session: Session = Depends(get_db),
    format: Optional[str] = None,
    admin_user: str = Depends(require_admin),
) -> str:
    """Get system health status as HTML."""
    db_healthy = _is_database_healthy(session)
    storage_healthy = _is_storage_healthy()

    health = HealthResponse(
        api_healthy=True,
        db_healthy=db_healthy,
        storage_healthy=storage_healthy,
        memory_usage_percent=_get_memory_usage_percent(),
        cpu_usage_percent=_get_cpu_usage_percent(),
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
    runtime_metrics = get_runtime_metrics()

    return f"""
    <div style="padding: var(--spacing-lg); border-bottom: 1px solid var(--border-color);">
        <h3>Performance Metrics</h3>
    </div>
    <div style="padding: var(--spacing-lg);">
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: var(--spacing-lg);">
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">Requests/sec</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">{runtime_metrics['requests_per_sec']:.2f}</div>
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">Avg Response Time</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">{runtime_metrics['avg_response_ms']:.1f}ms</div>
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">Error Rate</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">{runtime_metrics['error_rate_percent']:.1f}%</div>
            </div>
            <div style="background: var(--bg-secondary); padding: var(--spacing-lg); border-radius: 4px; text-align: center;">
                <div style="font-size: 0.875rem; color: var(--text-secondary);">DB Query Time</div>
                <div style="font-size: 1.75rem; font-weight: 600; margin-top: var(--spacing-sm);">{runtime_metrics['avg_db_query_ms']:.1f}ms</div>
            </div>
        </div>
    </div>
    """


# Users management endpoints
@router.get("/users", response_class=HTMLResponse)
async def get_admin_users_list(
    format: Optional[str] = None,
    request: Request = None,
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> str:
    """Get list of all users as HTML table."""
    # Fetch users from database
    service = UserService(session)
    users = service.list_users(skip=0, limit=1000)
    
    user_rows = ""
    for user in users:
        role = "admin" if user.is_admin else "user"
        created_at = user.created_at or "Unknown"
        status_label = "active" if user.is_active else "disabled"
        user_rows += f"""
            <tr>
                <td style="padding: var(--spacing-md);">{html.escape(user.username)}</td>
                <td style="padding: var(--spacing-md); color: var(--text-secondary);">{html.escape(user.nickname)}</td>
                <td style="padding: var(--spacing-md);">{html.escape(user.display_name)}</td>
                <td style="padding: var(--spacing-md);">{html.escape(user.email)}</td>
                <td style="padding: var(--spacing-md);">
                    <span style="background: var(--primary); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                        {role}
                    </span>
                </td>
                <td style="padding: var(--spacing-md);">
                    <span style="background: var(--bg-secondary); color: var(--text-primary); padding: 2px 8px; border-radius: 4px; font-size: 0.75rem;">
                        {status_label}
                    </span>
                </td>
                <td style="padding: var(--spacing-md); color: var(--text-secondary); font-size: 0.875rem;">{created_at}</td>
                <td style="padding: var(--spacing-md); text-align: right;">
                    <button class="btn btn-sm btn-secondary" hx-get="/api/v1/admin/users/{user.id}/edit-modal" hx-target="body" hx-swap="beforeend">
                        Edit
                    </button>
                </td>
            </tr>
            """
    
    return f"""
    <table style="width: 100%; border-collapse: collapse;">
        <thead style="border-bottom: 2px solid var(--border-color);">
            <tr>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Username</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Nickname</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Display Name</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Email</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Role</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Status</th>
                <th style="padding: var(--spacing-md); text-align: left; font-weight: 600;">Joined</th>
                <th style="padding: var(--spacing-md); text-align: right; font-weight: 600;">Action</th>
            </tr>
        </thead>
        <tbody>
            {user_rows}
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
    if request is None:
        raise HTTPException(status_code=500, detail="Request context is required")

    plugin_manager = _get_plugin_manager(request)
    plugins = plugin_manager.list_plugins()

    if not plugins:
        return """
        <div style="padding: var(--spacing-lg); text-align: center;">
            <p style="color: var(--text-secondary); margin: 0;">No plugins discovered under PLUGINS_ROOT.</p>
        </div>
        """

    cards = []
    for plugin in plugins:
        warnings_html = ""
        if plugin.warnings:
            warnings_html = "".join(
                f'<li style="margin: var(--spacing-xs) 0; color: var(--color-warning);">{html.escape(warning)}</li>'
                for warning in plugin.warnings
            )
            warnings_html = f"<ul style=\"margin: var(--spacing-sm) 0 0 0; padding-left: var(--spacing-lg);\">{warnings_html}</ul>"

        themes_summary = ", ".join(html.escape(theme.theme_name) for theme in plugin.themes) or "none"
        viewers_summary = ", ".join(html.escape(viewer.viewer_id) for viewer in plugin.viewers) or "none"
        display_status = plugin.status if plugin.status == "invalid" else ("enabled" if plugin.enabled else "disabled")
        status_color = "var(--success)" if display_status == "enabled" else "var(--warning)"
        next_enabled = "false" if plugin.enabled else "true"
        toggle_label = "Disable" if plugin.enabled else "Enable"

        cards.append(
            f"""
            <div style="padding: var(--spacing-lg); border: 1px solid var(--border-color); border-radius: 4px; display: grid; gap: var(--spacing-md);">
                <div style="display: flex; justify-content: space-between; gap: var(--spacing-md); align-items: flex-start;">
                    <div>
                        <h4 style="margin: 0 0 var(--spacing-xs) 0;">{html.escape(plugin.name)}</h4>
                        <p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem;">{html.escape(plugin.plugin_id)} · Version {html.escape(plugin.version)} · {html.escape(plugin.plugin_type)}</p>
                    </div>
                    <div style="display: flex; gap: var(--spacing-sm); align-items: center; flex-wrap: wrap; justify-content: flex-end;">
                        <span style="background: {status_color}; color: white; padding: 4px 12px; border-radius: 4px; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em;">{html.escape(display_status)}</span>
                        <button class="btn btn-sm btn-secondary" hx-get="/api/v1/admin/plugins/{html.escape(plugin.plugin_id)}/settings-modal" hx-target="body" hx-swap="beforeend">Settings YAML</button>
                        <button class="btn btn-sm {'btn-danger' if plugin.enabled else 'btn-primary'}" hx-post="/api/v1/admin/plugins/{html.escape(plugin.plugin_id)}/toggle" hx-vals='{{"enabled":"{next_enabled}"}}' hx-target="#plugins-list" hx-swap="innerHTML">{toggle_label}</button>
                    </div>
                </div>
                <p style="margin: 0; color: var(--text-secondary);">{html.escape(plugin.description or 'No description provided.')}</p>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--spacing-md); font-size: 0.875rem;">
                    <div>
                        <strong>Install Path</strong>
                        <p style="margin: var(--spacing-xs) 0 0 0; color: var(--text-secondary); word-break: break-all;">{html.escape(str(plugin.plugin_dir))}</p>
                    </div>
                    <div>
                        <strong>Theme Hooks</strong>
                        <p style="margin: var(--spacing-xs) 0 0 0; color: var(--text-secondary);">{themes_summary}</p>
                    </div>
                    <div>
                        <strong>Viewer Hooks</strong>
                        <p style="margin: var(--spacing-xs) 0 0 0; color: var(--text-secondary);">{viewers_summary}</p>
                    </div>
                    <div>
                        <strong>Settings File</strong>
                        <p style="margin: var(--spacing-xs) 0 0 0; color: var(--text-secondary); word-break: break-all;">{html.escape(str(plugin.settings_path))}</p>
                    </div>
                </div>
                <p style="margin: 0; font-size: 0.875rem; color: var(--text-tertiary);">Changes to enable state and YAML are saved immediately, but plugin discovery and activation still occur on application restart in v1.</p>
                {warnings_html}
            </div>
            """
        )

    return f'<div style="display: grid; gap: var(--spacing-lg);">{"".join(cards)}</div>'


@router.get("/plugins/{plugin_id}/settings-modal", response_class=HTMLResponse)
async def get_plugin_settings_modal(
    plugin_id: str,
    request: Request,
    admin_user: str = Depends(require_admin),
) -> str:
    """Open a modal editor for a plugin settings.yaml file."""
    plugin_manager = _get_plugin_manager(request)
    try:
        plugin = plugin_manager.get_plugin(plugin_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Plugin not found") from exc

    settings_text = html.escape(plugin_manager.get_plugin_settings_text(plugin_id))
    return f"""
    <div id="plugin-settings-modal" class="modal" style="display: flex; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); align-items: center; justify-content: center; z-index: 1000;">
      <div class="card" style="max-width: 860px; width: min(95vw, 860px); max-height: 90vh; overflow: auto;">
        <div style="padding: var(--spacing-lg); border-bottom: 1px solid var(--border-color); display: flex; justify-content: space-between; align-items: center; gap: var(--spacing-md);">
          <div>
            <h2 style="margin: 0;">{html.escape(plugin.name)} Settings</h2>
            <p style="margin: var(--spacing-xs) 0 0 0; color: var(--text-secondary); font-size: 0.875rem;">Editing {html.escape(str(plugin.settings_path))}</p>
          </div>
          <button hx-on="click: this.closest('#plugin-settings-modal').remove()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: var(--text-secondary);">×</button>
        </div>
        <form hx-post="/api/v1/admin/plugins/{html.escape(plugin.plugin_id)}/settings" hx-target="#plugin-settings-feedback" hx-swap="innerHTML">
          <div style="padding: var(--spacing-lg); display: grid; gap: var(--spacing-md);">
            <p style="margin: 0; color: var(--text-secondary); font-size: 0.875rem;">This writes the plugin-owned <strong>settings.yaml</strong>. Manifest metadata in <strong>plugin.yaml</strong> remains read-only.</p>
            <textarea name="settings_text" spellcheck="false" style="width: 100%; min-height: 420px; font-family: monospace; font-size: 0.9rem; line-height: 1.5; padding: var(--spacing-md); border: 1px solid var(--border-color); border-radius: 4px; background: var(--bg-secondary); color: var(--text-primary);">{settings_text}</textarea>
            <div id="plugin-settings-feedback"></div>
          </div>
          <div style="padding: var(--spacing-lg); border-top: 1px solid var(--border-color); display: flex; gap: var(--spacing-md); justify-content: flex-end;">
            <button type="button" class="btn btn-secondary" onclick="this.closest('#plugin-settings-modal').remove();">Close</button>
            <button type="submit" class="btn btn-primary">Save settings.yaml</button>
          </div>
        </form>
      </div>
    </div>
    """


@router.post("/plugins/{plugin_id}/settings", response_class=HTMLResponse)
async def save_plugin_settings(
    plugin_id: str,
    request: Request,
    settings_text: str = Form(...),
    admin_user: str = Depends(require_admin),
) -> HTMLResponse:
    """Validate and save plugin settings.yaml content."""
    plugin_manager = _get_plugin_manager(request)
    try:
        plugin_manager.save_plugin_settings(plugin_id, settings_text)
    except KeyError:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": "Plugin not found", "errors": {}},
            status_code=404,
        )
    except Exception as exc:
        logger.warning("Failed to save plugin settings for %s: %s", plugin_id, exc)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Could not save settings.yaml",
                "errors": {"settings.yaml": [str(exc)]},
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        "fragments/success-alert.html",
        {
            "request": request,
            "message": "settings.yaml saved. Restart the application to apply plugin configuration changes.",
        },
        status_code=200,
    )


@router.post("/plugins/{plugin_id}/toggle", response_class=HTMLResponse)
async def toggle_plugin_enabled(
    plugin_id: str,
    request: Request,
    enabled: str = Form(...),
    admin_user: str = Depends(require_admin),
) -> str:
    """Persist plugin enable state and refresh the admin list."""
    plugin_manager = _get_plugin_manager(request)
    try:
        plugin_manager.set_plugin_enabled(
            plugin_id,
            enabled.lower() in {"true", "1", "yes", "on"},
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Plugin not found") from exc

    return await get_admin_plugins_list(format="html", request=request, admin_user=admin_user)


@router.post("/plugins/reload", response_class=HTMLResponse)
async def reload_plugins(
    request: Request,
    admin_user: str = Depends(require_admin),
) -> HTMLResponse:
    """Reload plugin registry and derived theme/viewer contributions at runtime."""
    del admin_user
    plugin_manager = _get_plugin_manager(request)

    try:
        await plugin_manager.load_plugins(request.app, {})
        theme_manager = getattr(request.app.state, "theme_manager", None)
        if theme_manager is not None:
            await theme_manager.load_themes()
    except Exception as exc:
        logger.error("Failed to reload plugins: %s", exc)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Plugin reload failed",
                "errors": {"plugins": [str(exc)]},
            },
            status_code=500,
        )

    return templates.TemplateResponse(
        "fragments/success-alert.html",
        {
            "request": request,
            "message": "Plugins reloaded. New viewer hooks are now active.",
        },
        status_code=200,
    )


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
    <table style="width: 100%; border-collapse: collapse; font-size: 0.875rem; table-layout: fixed;">
        <colgroup>
            <col style="width: 14em;">
            <col style="width: 6em;">
            <col style="width: 8em;">
            <col style="width: 8em;">
            <col style="width: auto;">
        </colgroup>
        <thead style="border-bottom: 1px solid var(--border-color);">
            <tr>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Timestamp</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Level</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">User</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">IP</th>
                <th style="padding: var(--spacing-sm); text-align: left; font-weight: 600;">Message</th>
            </tr>
        </thead>
        <tbody>
            {"".join(f'''
            <tr style="border-bottom: 1px solid var(--border-color);">
                <td style="padding: var(--spacing-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{html.escape(log["timestamp"])}</td>
                <td style="padding: var(--spacing-sm);">
                    <span style="background: var(--bg-secondary); padding: 2px 6px; border-radius: 3px; font-size: 0.75rem;">
                        {html.escape(log["level"])}</span>
                </td>
                <td style="padding: var(--spacing-sm); color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis;" title="{html.escape(log["user_id"])}">{html.escape(log["username"] or log["user_id"] or "—")}</td>
                <td style="padding: var(--spacing-sm); color: var(--text-secondary);">{html.escape(log["client_ip"] or "—")}</td>
                <td style="padding: var(--spacing-sm); overflow: hidden; text-overflow: ellipsis;">{html.escape(log["message"])}</td>
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
    """Update API settings.
    
    Configure API metadata displayed in OpenAPI/Swagger documentation and file upload limits.
    
    Args:
        request: AdminSettingsRequest with optional fields:
            - api_title: Display name shown in API explorer (e.g., '3DKenji API')
            - api_version: Version string in OpenAPI spec (e.g., '1.0.0')
            - max_upload_mb: Maximum file upload size in MB (default 50 MB)
    
    Returns:
        JSON response with updated settings and confirmation message.
    
    Note:
        Settings are stored but not yet persisted to database. TODO: Database integration.
    """
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


@router.post("/settings/smtp", response_class=HTMLResponse)
async def update_smtp_settings(
    request: Request,
    host: str = Form(""),
    port: int = Form(587),
    username: str = Form(""),
    password: str = Form(""),
    from_email: str = Form(""),
    from_name: str = Form("3DKenji"),
    use_starttls: Optional[str] = Form(None),
    use_tls: Optional[str] = Form(None),
    mock_delivery: Optional[str] = Form(None),
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> HTMLResponse:
    """Persist SMTP settings used for invitation emails."""
    try:
        normalized = SMTPSettingsRequest(
            host=host.strip(),
            port=port,
            username=username.strip(),
            password=password,
            from_email=from_email.strip(),
            from_name=from_name.strip() or "3DKenji",
            use_starttls=bool(use_starttls),
            use_tls=bool(use_tls),
            mock_delivery=bool(mock_delivery),
        )

        if normalized.use_starttls and normalized.use_tls:
            raise ValueError("Choose either STARTTLS or SMTPS TLS, not both")

        settings = AppSettingsService(session).update_smtp_settings(
            normalized.dict(),
            updated_by=admin_user,
        )
        safe_settings = settings.copy()
        if safe_settings.get("password"):
            safe_settings["password"] = "***configured***"

        return templates.TemplateResponse(
            "fragments/success-alert.html",
            {
                "request": request,
                "message": f"SMTP settings saved for host {safe_settings.get('host', '')}",
            },
            status_code=200,
        )
    except Exception as exc:
        logger.warning("Failed to update SMTP settings: %s", exc)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Could not save SMTP settings",
                "errors": {"smtp": [str(exc)]},
            },
            status_code=400,
        )


# Clear logs endpoint
@router.post("/logs/clear")
async def clear_logs(
    admin_user: str = Depends(require_admin),
):
    """Clear all log files (primary and all rotated backups)."""
    cleared: list[str] = []
    errors: list[str] = []
    for path in _get_log_file_candidates():
        try:
            with path.open("w", encoding="utf-8"):
                pass
            cleared.append(str(path))
        except Exception as exc:
            logger.error("Failed to clear log file %s: %s", path, exc)
            errors.append(str(path))

    if errors and not cleared:
        raise HTTPException(status_code=500, detail="Failed to clear logs")

    logger.info("Logs cleared by admin", extra={"user_id": admin_user, "detail": f"cleared={cleared}"})
    return {"message": f"Cleared {len(cleared)} log file(s)", "cleared": cleared}


# Log settings endpoints
@router.get("/settings/logging")
async def get_log_settings(
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
):
    """Return current logging configuration."""
    from backend.logging_config import get_current_log_level, get_current_backup_count, get_current_max_size_mb
    db_settings = AppSettingsService(session).get_log_settings()
    # Reflect actual live values (may differ from DB if a restart applied env overrides)
    return {
        "log_level": get_current_log_level(),
        "max_size_mb": get_current_max_size_mb(),
        "backup_count": get_current_backup_count(),
        "db_settings": db_settings,
    }


@router.post("/settings/logging", response_class=HTMLResponse)
async def update_log_settings(
    request: Request,
    log_level: Optional[str] = Form(None),
    max_size_mb: Optional[int] = Form(None),
    backup_count: Optional[int] = Form(None),
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> HTMLResponse:
    """Update logging level, max file size, and backup count. Persists to DB and applies live."""
    from backend.logging_config import configure_logging

    try:
        validated = LogSettingsRequest(
            log_level=log_level,
            max_size_mb=max_size_mb,
            backup_count=backup_count,
        )
        payload: dict = {}
        if validated.log_level is not None:
            payload["log_level"] = validated.log_level
        if validated.max_size_mb is not None:
            payload["max_size_mb"] = validated.max_size_mb
        if validated.backup_count is not None:
            payload["backup_count"] = validated.backup_count

        if not payload:
            return templates.TemplateResponse(
                "fragments/error-alert.html",
                {"request": request, "message": "No settings provided", "errors": {}},
                status_code=400,
            )

        # Persist to DB (merge with existing)
        settings_service = AppSettingsService(session)
        saved = settings_service.update_log_settings(payload, updated_by=admin_user)

        # Apply to live logger immediately
        configure_logging(
            log_level=saved["log_level"],
            max_size_mb=saved["max_size_mb"],
            backup_count=saved["backup_count"],
        )

        logger.info(
            "Log settings updated by admin",
            extra={
                "user_id": admin_user,
                "detail": f"level={saved['log_level']} max_size_mb={saved['max_size_mb']} backup_count={saved['backup_count']}",
            },
        )

        return templates.TemplateResponse(
            "fragments/success-alert.html",
            {
                "request": request,
                "message": (
                    f"Logging updated: level={saved['log_level']}, "
                    f"max_size={saved['max_size_mb']} MB, "
                    f"backups={saved['backup_count']}"
                ),
            },
            status_code=200,
        )
    except Exception as exc:
        logger.warning("Failed to update log settings: %s", exc)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": f"Could not update log settings: {exc}", "errors": {}},
            status_code=400,
        )


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
        "nickname": user.nickname,
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
    request: Request,
    username: str = Form(...),
    nickname: Optional[str] = Form(None),
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    is_active: str = Form(default="true"),
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> str:
    """Create a new user."""
    try:
        # Validate role
        if role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'user' or 'admin'")
        
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
        is_admin = (role == "admin")
        is_user_active = is_active.lower() in ("true", "on", "yes", "1")
        user_service.create_user(
            username=username,
            nickname=nickname,
            email=email,
            display_name=display_name,
            password=password,
            is_admin=is_admin,
            is_active=is_user_active,
        )

        logger.info(
            "ADMIN_USER_CREATED",
            extra={
                "event": "admin_user_created",
                "user_id": admin_user,
                "detail": f"new_username={username!r} role={role} is_active={is_user_active}",
            },
        )

        return templates.TemplateResponse(
            "fragments/success-alert.html",
            {"request": request, "message": "User created successfully"},
            status_code=201,
        )
    except HTTPException as exc:
        logger.warning("Failed to create user: %s", exc.detail)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": str(exc.detail), "errors": {}},
            status_code=exc.status_code,
        )
    except Exception as e:
        logger.error("Failed to create user: %s", e)
        session.rollback()
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Failed to create user",
                "errors": {"general": [str(e)]},
            },
            status_code=500,
        )


@router.put("/users/{user_id}", response_class=HTMLResponse)
async def update_user(
    user_id: str,
    request: Request,
    username: Optional[str] = Form(None),  # Ignored, but accepted to prevent validation errors
    nickname: str = Form(...),
    email: str = Form(...),
    display_name: str = Form(...),
    password: Optional[str] = Form(default=""),  # Optional - empty or missing means keep current password
    role: str = Form(...),
    is_active: str = Form(default="true"),
    session: Session = Depends(get_db),
    admin_user: str = Depends(require_admin),
) -> str:
    """Update an existing user."""
    try:
        # Convert empty/None password to None (keep existing password)
        if password == "" or password is None:
            password = None
        
        # Validate role
        if role not in ("user", "admin"):
            raise HTTPException(status_code=400, detail="Invalid role. Must be 'user' or 'admin'")
        
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
        
        service = UserService(session)

        # Apply user-editable fields exactly like user profile flow.
        service.update_profile(
            user_id=user_id,
            email=email,
            display_name=display_name,
            nickname=nickname,
        )

        # Refresh ORM user after profile update commit.
        user = session.execute(
            select(User).where(User.id == user_id)
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.is_admin = (role == "admin")
        is_user_active = is_active.lower() in ("true", "on", "yes", "1")
        user.is_active = is_user_active
        
        # Update password if provided
        if password:
            service.update_password(user_id=user_id, new_password=password)
            user = session.execute(
                select(User).where(User.id == user_id)
            ).scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
        
        session.commit()

        logger.info(
            "ADMIN_USER_UPDATED",
            extra={
                "event": "admin_user_updated",
                "user_id": admin_user,
                "detail": f"target_user_id={user_id} role={role} is_active={is_user_active}",
            },
        )

        return templates.TemplateResponse(
            "fragments/success-alert.html",
            {"request": request, "message": "User updated successfully"},
            status_code=200,
        )
    except HTTPException as exc:
        logger.warning("Failed to update user: %s", exc.detail)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {"request": request, "message": str(exc.detail), "errors": {}},
            status_code=exc.status_code,
        )
    except Exception as e:
        logger.error("Failed to update user: %s", e)
        session.rollback()
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Failed to update user",
                "errors": {"general": [str(e)]},
            },
            status_code=500,
        )


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


@router.post("/plugins/upload", response_class=HTMLResponse)
async def upload_plugin(
    request: Request,
    plugin_file: UploadFile = File(...),
    admin_user: str = Depends(require_admin),
) -> HTMLResponse:
    """Handle plugin upload form submission (validation + placeholder install flow)."""
    if not plugin_file.filename:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "No plugin file provided",
                "errors": {"plugin_file": ["Please choose a plugin ZIP file"]},
            },
            status_code=400,
        )

    if not plugin_file.filename.lower().endswith(".zip"):
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Invalid plugin package",
                "errors": {"plugin_file": ["Plugin package must be a .zip file"]},
            },
            status_code=400,
        )

    # Placeholder for plugin installation workflow.
    return templates.TemplateResponse(
        "fragments/success-alert.html",
        {
            "request": request,
            "message": f"Plugin package '{plugin_file.filename}' uploaded successfully",
        },
        status_code=201,
    )
