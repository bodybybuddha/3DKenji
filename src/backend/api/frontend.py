"""Frontend routes for serving HTML and theme CSS."""

import logging
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.core.validation import SetupRequest, format_validation_errors
from backend.core.auth import decode_token
from backend.db import get_db
from backend.services.project_directory import (
    PathNotFoundError,
    PathTraversalError,
    get_projects_dir,
    service_for_project,
)
from backend.services.project_service import ProjectService
from backend.services.user_service import UserService

logger = logging.getLogger(__name__)

# Initialize templates
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


# Register custom Jinja2 filters
def timeago_filter(dt):
    """Convert a datetime to a human-readable 'time ago' string."""
    if dt is None:
        return "Unknown"
    
    # Ensure dt is a datetime object
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return str(dt)
    
    now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
    diff = now - dt
    
    seconds = diff.total_seconds()
    
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    elif seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    elif seconds < 31536000:
        months = int(seconds / 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"
    else:
        years = int(seconds / 31536000)
        return f"{years} year{'s' if years != 1 else ''} ago"


def dateformat_filter(dt):
    """Format datetime in a short readable date format."""
    if dt is None:
        return "Never"

    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception:
            return str(dt)

    return dt.strftime("%Y-%m-%d")


def filesizeformat_filter(size):
    """Convert bytes to human-readable file size."""
    try:
        size = float(size or 0)
    except (TypeError, ValueError):
        return "0 B"

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


templates.env.filters["timeago"] = timeago_filter
templates.env.filters["dateformat"] = dateformat_filter
templates.env.filters["filesizeformat"] = filesizeformat_filter

router = APIRouter(tags=["frontend"])


# Helper functions for authentication
async def get_optional_user(request: Request, session: Session):
    """
    Extract user from JWT cookie if present.
    Returns None if no token or token is invalid.
    """
    try:
        token = request.cookies.get("access_token")
        if not token:
            return None
        
        # Decode token
        payload = decode_token(token)
        
        # Load user from database
        user_service = UserService(session)
        user = user_service.get_user_by_id(payload.user_id)
        
        if not user:
            return None
        
        return user
    except Exception as e:
        logger.debug(f"Failed to get user from cookie: {e}")
        return None


# Theme router - separated for clarity
def create_theme_router(theme_manager):
    """Create theme routes using the provided theme manager."""
    theme_router = APIRouter(prefix="/api/v1/theme", tags=["theme"])
    
    @theme_router.get("/list")
    async def list_themes():
        """List available themes."""
        themes = await theme_manager.list_themes()
        return {"themes": themes}
    
    @theme_router.get("/css/{theme_name}")
    async def get_theme_css(theme_name: str):
        """
        Get CSS for a theme.
        
        Returns CSS with theme-specific CSS variables.
        """
        try:
            css = await theme_manager.get_theme_css(theme_name)
            return StreamingResponse(
                iter([css]),
                media_type="text/css",
                headers={"Cache-Control": "public, max-age=3600"}
            )
        except ValueError:
            return StreamingResponse(
                iter([":root {}"]),  # Empty CSS on error
                media_type="text/css",
                status_code=404
            )
    
    @theme_router.get("/variables/{theme_name}")
    async def get_theme_variables(theme_name: str):
        """Get CSS variables as JSON for a theme."""
        try:
            variables = await theme_manager.get_theme_variables(theme_name)
            return {
                "theme": theme_name,
                "variables": variables
            }
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    
    return theme_router


# HTML routes
@router.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Session = Depends(get_db)):
    """Home/landing page."""
    user = await get_optional_user(request, session)
    return templates.TemplateResponse("index.html", {"request": request, "user": user})


@router.get("/setup", response_class=HTMLResponse)
async def setup(request: Request):
    """Setup/first-time configuration page."""
    if not getattr(request.app.state, "setup_required", False):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("setup.html", {"request": request})


@router.post("/setup", response_class=HTMLResponse)
async def setup_submit(
    request: Request,
    username: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    password_confirm: str = Form(""),
    theme: str = Form("dark"),
    session=Depends(get_db),
):
    """Handle first-time setup form submission."""
    if not getattr(request.app.state, "setup_required", False):
        return RedirectResponse(url="/login", status_code=303)

    try:
        validated = SetupRequest(
            username=username,
            email=email,
            password=password,
            password_confirm=password_confirm,
            theme=theme,
        )
        
        user_service = UserService(session)
        user_service.create_user(
            username=validated.username,
            email=validated.email,
            display_name=validated.username,
            password=validated.password,
            is_admin=True,
            is_active=True,
        )

        request.app.state.setup_required = False

        return templates.TemplateResponse(
            "fragments/success-alert.html",
            {
                "request": request,
                "message": "Admin account created. Redirecting to login...",
            },
        )
    except ValidationError as e:
        errors = format_validation_errors(e)
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": "Validation failed",
                "errors": errors,
            },
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": str(e),
                "errors": {"general": [str(e)]},
            },
        )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, session: Session = Depends(get_db)):
    """Login page."""
    user = await get_optional_user(request, session)
    # Redirect to projects if already logged in
    if user:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("auth/login.html", {"request": request, "user": None})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, session: Session = Depends(get_db)):
    """Registration page."""
    user = await get_optional_user(request, session)
    # Redirect to projects if already logged in
    if user:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("auth/register.html", {"request": request, "user": None})


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request, session: Session = Depends(get_db)):
    """Projects list page."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    projects: list[dict] = []
    try:
        service = ProjectService(session)
        projects = [p.__dict__ for p in service.list_user_projects(owner_id=user.id)]
    except Exception as exc:
        logger.warning("Failed to load projects for page render: %s", exc)

    return templates.TemplateResponse(
        "projects/list.html",
        {
            "request": request,
            "user": user,
            "projects": projects,
        },
    )


@router.get("/projects/create-modal", response_class=HTMLResponse)
async def get_create_project_modal(
    request: Request,
    session: Session = Depends(get_db)
) -> str:
    """Get the create project modal form."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    return templates.TemplateResponse("projects/form-modal.html", {
        "request": request,
    }).body.decode()


@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str, session: Session = Depends(get_db)):
    """Project detail page."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    project_fs_path = get_projects_dir() / project.category / project.slug
    project_info_path = project_fs_path / "ProjectInfo.md"

    return templates.TemplateResponse(
        "projects/detail.html",
        {
            "request": request,
            "project_id": project_id,
            "project": project,
            "user": user,
            "project_fs_path": str(project_fs_path),
            "project_info_exists": project_info_path.exists(),
            "project_directory_exists": project_fs_path.exists(),
        },
    )


@router.get("/projects/{project_id}/upload-modal", response_class=HTMLResponse)
async def get_upload_model_modal(
    request: Request,
    project_id: str,
    session: Session = Depends(get_db),
) -> str:
    """Get the upload model modal for a project owned by current user."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    return templates.TemplateResponse(
        "projects/upload-modal.html",
        {"request": request, "project_id": project_id},
    ).body.decode()


@router.get("/projects/{project_id}/files/editor", response_class=HTMLResponse)
async def project_file_editor_page(
    request: Request,
    project_id: str,
    path: str,
    session: Session = Depends(get_db),
) -> HTMLResponse:
    """Open the standalone text editor window for a project file."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    project_service = ProjectService(session)
    project = project_service.get_project_by_id(project_id)
    if not project or project.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    extension = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    editable_extensions = {
        "txt", "md", "markdown", "rtf", "log", "json", "yaml", "yml", "csv",
        "ini", "cfg", "conf", "toml", "xml", "html", "css", "js", "ts", "py",
        "gcode", "sql", "sh",
    }
    if extension not in editable_extensions:
        raise HTTPException(status_code=400, detail="File type is not editable")

    directory_service = service_for_project(project.category, project.slug)
    try:
        directory_service.read_file(path)
    except PathTraversalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PathNotFoundError as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    except IsADirectoryError as exc:
        raise HTTPException(status_code=400, detail="Path is a directory") from exc

    return templates.TemplateResponse(
        "projects/file-editor.html",
        {
            "request": request,
            "project_id": project_id,
            "project": project,
            "file_path": path,
            "file_name": path.split("/")[-1],
            "extension": extension,
            "is_markdown": extension in {"md", "markdown"},
            "is_rtf": extension == "rtf",
            "user": user,
        },
    )


@router.get("/keys", response_class=HTMLResponse)
async def api_keys_page(request: Request, session: Session = Depends(get_db)):
    """API keys management page."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("keys/list.html", {"request": request, "user": user})


@router.get("/settings/profile", response_class=HTMLResponse)
async def profile_settings(request: Request, session: Session = Depends(get_db)):
    """User profile settings page."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("settings/profile.html", {"request": request, "user": user})


@router.post("/settings/profile", response_class=HTMLResponse)
async def update_profile(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    session: Session = Depends(get_db)
):
    """Update user profile."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Update user profile
        user_service = UserService(session)
        user.email = email
        user.display_name = display_name
        session.commit()
        
        # Return success message as HTML fragment
        return HTMLResponse(
            content='''
            <form hx-post="/settings/profile" hx-swap="outerHTML" id="profile-form" class="card-body">
                <div class="form-group">
                    <label for="username" class="form-label">Username</label>
                    <input type="text" id="username" name="username" class="form-input" disabled
                        value="''' + user.username + '''" />
                    <small style="color: var(--text-tertiary);">Cannot be changed</small>
                </div>

                <div class="form-group">
                    <label for="email" class="form-label required">Email</label>
                    <input type="email" id="email" name="email" class="form-input" required
                        value="''' + user.email + '''" />
                </div>

                <div class="form-group">
                    <label for="display_name" class="form-label">Display Name</label>
                    <input type="text" id="display_name" name="display_name" class="form-input"
                        value="''' + user.display_name + '''" />
                </div>

                <div style="display: flex; gap: var(--spacing-md);">
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                    <button type="reset" class="btn btn-secondary">Cancel</button>
                </div>
            </form>
            <script>
                HTMXHelper.showToast('Profile updated successfully!', 'success');
            </script>
            ''',
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to update profile: {e}")
        return HTMLResponse(
            content=f'<div class="alert alert-danger">Failed to update profile: {str(e)}</div>',
            status_code=400
        )


@router.post("/settings/password", response_class=HTMLResponse)
async def update_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    session: Session = Depends(get_db)
):
    """Update user password."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    try:
        # Verify current password
        from backend.plugins.auth_password import PasswordAuthProvider
        auth_provider = PasswordAuthProvider()
        
        if not auth_provider.verify_password(current_password, user.password_hash):
            return HTMLResponse(
                content='''
                <form hx-post="/settings/password" hx-swap="outerHTML" id="password-form" class="card-body">
                    <div class="alert alert-danger">Current password is incorrect</div>
                    <div class="form-group">
                        <label for="current_password" class="form-label required">Current Password</label>
                        <input type="password" id="current_password" name="current_password" class="form-input" required />
                    </div>

                    <div class="form-group">
                        <label for="new_password" class="form-label required">New Password</label>
                        <input type="password" id="new_password" name="new_password" class="form-input" required
                            minlength="8" />
                        <small style="color: var(--text-tertiary);">At least 8 characters</small>
                    </div>

                    <div class="form-group">
                        <label for="new_password_confirm" class="form-label required">Confirm New Password</label>
                        <input type="password" id="new_password_confirm" name="new_password_confirm" class="form-input"
                            required minlength="8" />
                    </div>

                    <div style="display: flex; gap: var(--spacing-md);">
                        <button type="submit" class="btn btn-primary">Update Password</button>
                        <button type="reset" class="btn btn-secondary">Cancel</button>
                    </div>
                </form>
                ''',
                status_code=400
            )
        
        # Verify passwords match
        if new_password != new_password_confirm:
            return HTMLResponse(
                content='''
                <form hx-post="/settings/password" hx-swap="outerHTML" id="password-form" class="card-body">
                    <div class="alert alert-danger">New passwords do not match</div>
                    <div class="form-group">
                        <label for="current_password" class="form-label required">Current Password</label>
                        <input type="password" id="current_password" name="current_password" class="form-input" required />
                    </div>

                    <div class="form-group">
                        <label for="new_password" class="form-label required">New Password</label>
                        <input type="password" id="new_password" name="new_password" class="form-input" required
                            minlength="8" />
                        <small style="color: var(--text-tertiary);">At least 8 characters</small>
                    </div>

                    <div class="form-group">
                        <label for="new_password_confirm" class="form-label required">Confirm New Password</label>
                        <input type="password" id="new_password_confirm" name="new_password_confirm" class="form-input"
                            required minlength="8" />
                    </div>

                    <div style="display: flex; gap: var(--spacing-md);">
                        <button type="submit" class="btn btn-primary">Update Password</button>
                        <button type="reset" class="btn btn-secondary">Cancel</button>
                    </div>
                </form>
                ''',
                status_code=400
            )
        
        # Update password
        user.password_hash = auth_provider.hash_password(new_password)
        session.commit()
        
        # Return success message
        return HTMLResponse(
            content='''
            <form hx-post="/settings/password" hx-swap="outerHTML" id="password-form" class="card-body">
                <div class="form-group">
                    <label for="current_password" class="form-label required">Current Password</label>
                    <input type="password" id="current_password" name="current_password" class="form-input" required />
                </div>

                <div class="form-group">
                    <label for="new_password" class="form-label required">New Password</label>
                    <input type="password" id="new_password" name="new_password" class="form-input" required
                        minlength="8" />
                    <small style="color: var(--text-tertiary);">At least 8 characters</small>
                </div>

                <div class="form-group">
                    <label for="new_password_confirm" class="form-label required">Confirm New Password</label>
                    <input type="password" id="new_password_confirm" name="new_password_confirm" class="form-input"
                        required minlength="8" />
                </div>

                <div style="display: flex; gap: var(--spacing-md);">
                    <button type="submit" class="btn btn-primary">Update Password</button>
                    <button type="reset" class="btn btn-secondary">Cancel</button>
                </div>
            </form>
            <script>
                HTMXHelper.showToast('Password updated successfully!', 'success');
                document.getElementById('password-form').reset();
            </script>
            ''',
            status_code=200
        )
    except Exception as e:
        logger.error(f"Failed to update password: {e}")
        return HTMLResponse(
            content=f'<div class="alert alert-danger">Failed to update password: {str(e)}</div>',
            status_code=400
        )


@router.delete("/settings/account", response_class=HTMLResponse)
async def delete_account(
    request: Request,
    session: Session = Depends(get_db),
):
    """Delete currently authenticated account and clear auth cookie."""
    user = await get_optional_user(request, session)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user_service = UserService(session)
    if not user_service.delete_user(user.id):
        raise HTTPException(status_code=404, detail="User not found")

    response = Response(status_code=200)
    response.headers["HX-Redirect"] = "/"
    response.delete_cookie("access_token")
    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, session: Session = Depends(get_db)):
    """Admin dashboard page."""
    user = await get_optional_user(request, session)
    if not user or not user.is_admin:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("admin/dashboard.html", {"request": request, "user": user})


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request, session: Session = Depends(get_db)):
    """Admin users management page."""
    user = await get_optional_user(request, session)
    if not user or not user.is_admin:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("admin/users/list.html", {"request": request, "user": user})


@router.get("/admin/plugins", response_class=HTMLResponse)
async def admin_plugins(request: Request, session: Session = Depends(get_db)):
    """Admin plugins manager page."""
    user = await get_optional_user(request, session)
    if not user or not user.is_admin:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("admin/plugins/list.html", {"request": request, "user": user})


@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request, session: Session = Depends(get_db)):
    """Admin settings page."""
    user = await get_optional_user(request, session)
    if not user or not user.is_admin:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("admin/settings.html", {"request": request, "user": user})


@router.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(request: Request, session: Session = Depends(get_db)):
    """Admin logs viewer page."""
    user = await get_optional_user(request, session)
    if not user or not user.is_admin:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("admin/logs.html", {"request": request, "user": user})


@router.get("/admin/health", response_class=HTMLResponse)
async def admin_health(request: Request, session: Session = Depends(get_db)):
    """Admin system health page."""
    user = await get_optional_user(request, session)
    if not user or not user.is_admin:
        return RedirectResponse(url="/projects", status_code=303)
    return templates.TemplateResponse("admin/health.html", {"request": request, "user": user})

