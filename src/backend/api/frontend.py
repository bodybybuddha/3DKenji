"""Frontend routes for serving HTML and theme CSS."""

import logging
import os
from fastapi import APIRouter, HTTPException, Request, Depends, Form
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from backend.core.validation import SetupRequest, format_validation_errors
from backend.db import get_db
from backend.services.user_service import UserService

logger = logging.getLogger(__name__)

# Initialize templates
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
TEMPLATES_DIR = os.path.join(FRONTEND_DIR, "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(tags=["frontend"])


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
async def home(request: Request):
    """Home/landing page."""
    return templates.TemplateResponse("index.html", {"request": request})


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
            status_code=400,
        )
    except ValueError as e:
        return templates.TemplateResponse(
            "fragments/error-alert.html",
            {
                "request": request,
                "message": str(e),
                "errors": {"general": [str(e)]},
            },
            status_code=400,
        )


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page."""
    return templates.TemplateResponse("auth/login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Registration page."""
    return templates.TemplateResponse("auth/register.html", {"request": request})


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    """Projects list page."""
    return templates.TemplateResponse("projects/list.html", {"request": request})


@router.get("/project/{project_id}", response_class=HTMLResponse)
async def project_detail(request: Request, project_id: str):
    """Project detail page."""
    return templates.TemplateResponse("projects/detail.html", {"request": request, "project_id": project_id})


@router.get("/keys", response_class=HTMLResponse)
async def api_keys_page(request: Request):
    """API keys management page."""
    return templates.TemplateResponse("keys/list.html", {"request": request})


@router.get("/settings/profile", response_class=HTMLResponse)
async def profile_settings(request: Request):
    """User profile settings page."""
    return templates.TemplateResponse("settings/profile.html", {"request": request})


@router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard page."""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


@router.get("/admin/users", response_class=HTMLResponse)
async def admin_users(request: Request):
    """Admin users management page."""
    return templates.TemplateResponse("admin/users/list.html", {"request": request})


@router.get("/admin/plugins", response_class=HTMLResponse)
async def admin_plugins(request: Request):
    """Admin plugins manager page."""
    return templates.TemplateResponse("admin/plugins/list.html", {"request": request})


@router.get("/admin/settings", response_class=HTMLResponse)
async def admin_settings(request: Request):
    """Admin settings page."""
    return templates.TemplateResponse("admin/settings.html", {"request": request})


@router.get("/admin/logs", response_class=HTMLResponse)
async def admin_logs(request: Request):
    """Admin logs viewer page."""
    return templates.TemplateResponse("admin/logs.html", {"request": request})


@router.get("/admin/health", response_class=HTMLResponse)
async def admin_health(request: Request):
    """Admin system health page."""
    return templates.TemplateResponse("admin/health.html", {"request": request})

