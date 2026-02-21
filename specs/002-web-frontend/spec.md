# Feature Specification: Web UI Frontend

**Feature ID**: 002-web-frontend  
**Status**: In Progress  
**Start Date**: February 21, 2026  
**Target Completion**: March 11, 2026 (expanded for admin interface)  

---

## 1. Overview

Add a complete web-based user interface to 3DKenji using FastAPI + Jinja2 templates + HTMX. The frontend provides a modern, responsive UI with pluggable theming system (dark mode by default) while maintaining clean separation between presentation and business logic.

### Goals

✅ Create intuitive web interface for all API features  
✅ Implement pluggable theme system (colors via CSS variables only)  
✅ Use HTMX for interactive elements without heavy JavaScript framework  
✅ Maintain separation between frontend code and theme definitions  
✅ Enable easy addition of new themes and UI extensions  
✅ Ensure dark mode by default with light mode option  
✅ Build comprehensive admin interface for system management  
✅ Implement first-time setup flow (admin account creation)  
✅ Enable user, plugin, and configuration management

### Success Criteria

- [ ] All pages render correctly in dark and light modes
- [ ] Theme can be switched without page reload (HTMX)
- [ ] Theme preference persists across sessions (localStorage)
- [ ] New themes can be added as Python plugins
- [ ] No color values hardcoded in HTML/JavaScript
- [ ] Responsive design on mobile, tablet, desktop
- [ ] Common HTMX interactions work: form submission, deletion, filtering
- [ ] Authentication flows work with session management
- [ ] File upload for 3D models works with progress
- [ ] Search and pagination work via HTMX
- [ ] First-time setup creates admin account automatically
- [ ] Admin interface requires authentication and is_admin flag
- [ ] Admin can manage users (create, edit, delete, role assignment)
- [ ] Admin can view and manage plugins
- [ ] Admin can view application logs in real-time
- [ ] Admin can view system health and status
- [ ] Settings panel allows configuration changes

---

## 2. Architecture

### 2.1 Frontend Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Templates | Jinja2 | Server-side HTML generation |
| Styling | CSS Variables + HTMX | Dynamic theming, interactivity |
| Scripting | HTMX + Vanilla JS | Form submission, dynamic updates |
| Theming | Plugin System + CSS | Easy theme switching and extension |
| Icons | Bootstrap Icons (CDN) | Consistent iconography |
| Layout | CSS Grid/Flexbox | Responsive design |

### 2.2 Integration with Existing FastAPI

```
FastAPI Backend
├── REST API /api/v1/*           (existing, no changes)
├── HTML Pages /                 (new)
├── Theme API /api/v1/theme/*    (new)
└── Static Files /static/        (new)
```

**Key Decision**: Frontend and API coexist in same FastAPI app
- Simplifies deployment
- Single authentication system
- Sessions managed server-side
- Non-breaking to existing API clients

### 2.3 Theme Plugin System

**Purpose**: Allow new themes without touching HTML/JS code

**Plugin Interface**:
```python
class ThemePlugin(KeajiPlugin):
    name: str              # "dark", "light"
    version: str
    is_default: bool       # Dark theme is default
    css_variables: dict    # Color definitions
    
    async def get_css() -> str  # Generate CSS dynamically
```

**Theme Definition** (pure data):
```python
css_variables = {
    # Semantic colors
    "color-primary": "#3b82f6",
    "color-success": "#10b981",
    "color-danger": "#ef4444",
    "color-warning": "#f59e0b",
    
    # Backgrounds
    "bg-primary": "#1f2937",
    "bg-secondary": "#111827",
    
    # Text
    "text-primary": "#f3f4f6",
    "text-secondary": "#d1d5db",
}
```

**CSS Usage** (no color hardcoding):
```css
.button {
    background: var(--color-primary);
    color: var(--bg-primary);
}

.alert-success {
    background: var(--color-success);
}
```

### 2.4 HTMX Integration Strategy

**Use Cases**:
1. Form submission without page reload
2. Delete with confirmation dialog
3. Theme switching (no full page refresh)
4. Pagination without reload
5. Search filters with live results
6. Modal dialogs for edit/create

**Example**:
```html
<form hx-post="/projects/create"
      hx-target="#projects-list"
      hx-swap="beforeend">
  <input name="title" required>
  <button type="submit">Create</button>
</form>
```

### 2.5 Session Management

**Authentication Flow**:
1. User registers/logs in via `/register` or `/login` pages
2. Backend issues JWT token AND sets secure session cookie
3. Session cookie used for page requests (simpler)
4. JWT used for API requests (if needed for third-party clients)
5. Theme preference stored in localStorage (client-side)

**Logout**: Clear session cookie and redirect

---

## 3. Scope

### 3.1 Included (Phase 6A)

**Pages**:
- [x] Landing/Home page
- [x] User Registration page
- [x] User Login page
- [x] Projects list page (with pagination)
- [x] Project detail page
- [x] Create/Edit project modal
- [x] Models list (within project)
- [x] Model upload form
- [x] API Keys management page
- [x] User profile/settings page

**Components**:
- [x] Navigation bar with user menu
- [x] Theme switcher dropdown
- [x] File upload input with validation
- [x] Pagination controls
- [x] Alert/notification messages
- [x] Modal dialog for forms
- [x] Confirmation dialogs for deletion
- [x] Loading spinners for AJAX requests

**Theming**:
- [x] Dark theme (default) - full implementation
- [x] Light theme - full implementation
- [x] Theme switcher UI
- [x] Persistent theme preference

### 3.2 Excluded (Future Phases)

- 3D model viewer/renderer (future: Three.js integration)
- Real-time WebSocket updates
- Advanced filtering/search UI
- Print job tracking interface
- Mobile app
- Advanced analytics dashboard
- OAuth provider settings (basic auth only in MVP)
- Email notifications/SMTP configuration

---

## 4. User Flows

### 4.1 Authentication Flow

```
User
  ↓
[Home Page] → "Register" link
  ↓
[Register Page] → Submit form
  ↓
[FastAPI] → Validate & create user
  ↓
[Set Session Cookie + JWT] → Redirect
  ↓
[Projects List] → Authenticated view
```

### 4.2 Project Management Flow

```
[Projects List] → "Create Project" button
  ↓
[Modal Form] (HTMX) → Enter details
  ↓
[HTMX POST] → Create via API
  ↓
[Update DOM] → New project appears
  ↓
[Click Project] → Project detail page
```

### 4.3 Model Upload Flow

```
[Project Detail] → "Upload Model" section
  ↓
[File Input Form] → Select .stl/.3mf/.obj/.gcode
  ↓
[HTMX Multipart Upload] → POST to backend
  ↓
[Show Progress] → File uploading...
  ↓
[Update Models List] → New model appears
```

---

## 5. Admin Interface Architecture

### 5.1 First-Time Setup Flow

**Startup Process**:
1. App initializes database migrations (Alembic)
2. Check if any admin users exist in database
3. If no admins: Redirect to `/setup` page
4. If admins exist: Normal flow

**Setup Page**:
```
[Logo] 3DKenji Setup

Welcome! Let's set up your 3DKenji instance.

[Form]
Admin Username: ____________
Admin Email: ________________
Password: ___________________
Confirm: ____________________

Default Theme: [Dark] [Light]

[Create Admin Account and Continue]

After submission:
- Create admin user (is_admin=True)
- Set theme preference
- Redirect to /login
- Show "Admin account created. Please log in."
```

### 5.2 Admin Dashboard

**Overview**:
- System status cards (storage used, users count, projects count, uptime)
- Recent activity log
- Quick links to management sections
- System health status

**Navigation**:
```
Admin Dashboard
├── Dashboard (home)
├── Users → List, Create, Edit, Delete, Assign Roles
├── Plugins → View, Enable/Disable, Configure
├── Settings → Theme, Log Level, Backup
├── Logs → View, Filter, Download
└── System Health → Storage, Database, API Status
```

### 5.3 Admin Pages Layout

**User Management Page**:
- Table of users: username, email, role, created_date, last_login
- Create new user button → modal form
- Edit button per user → modal form
- Delete button with confirmation
- Filter/search by username or email
- Pagination for large user lists

**Plugin Manager Page**:
- List installed plugins: name, type, version, status
- Enable/disable toggle per plugin
- Configuration button per plugin (opens modal)
- View plugin details/dependencies
- Update available (future)

**Settings Page**:
- Theme selection dropdown
- Log level selection
- Backup/restore options
- Advanced settings (API rate limiting, etc.)

**Logs Viewer Page**:
- Real-time log display (tail logs)
- Filter by level (DEBUG, INFO, WARNING, ERROR)
- Filter by module/logger
- Search by message
- Download logs as file
- Auto-refresh toggle

**System Health Page**:
- Storage usage (total, used, available)
- Database connection status
- API response time metrics
- User/Project/Model counts
- Uptime information

---

## 6. Design System

### 6.1 Admin UI Components

**Additional Components for Admin**:
- Admin navigation sidebar or top nav
- Data tables with sorting and pagination
- Modal dialogs for confirmations and forms
- Badge components (status indicators)
- Progress bars (storage usage, etc.)
- Status cards with icons
- Toast notifications for actions
- Breadcrumb navigation

### 6.2 CSS Architecture

```
frontend/static/css/
├── index.css              # All imports
├── themes/
│   ├── dark.css          # Dark theme variables
│   └── light.css         # Light theme variables
├── components/
│   ├── buttons.css
│   ├── cards.css
│   ├── forms.css
│   ├── alerts.css
│   └── modals.css
├── layout/
│   ├── base.css         # Grid, flexbox layouts
│   ├── navbar.css
│   └── footer.css
└── utilities/
    ├── spacing.css      # Margins, padding
    ├── typography.css   # Fonts, sizes
    └── responsive.css   # Media queries
```

### 6.3 Color Variables

**Dark Theme** (default):
```css
:root {
  /* Semantic Colors - All interaction states */
  --color-primary: #3b82f6;         /* Blue - primary actions */
  --color-success: #10b981;         /* Green - success states */
  --color-danger: #ef4444;          /* Red - destructive actions */
  --color-warning: #f59e0b;         /* Amber - alerts */
  --color-info: #0ea5e9;            /* Cyan - informational */
  
  /* Backgrounds */
  --bg-primary: #1f2937;            /* Main background */
  --bg-secondary: #111827;          /* Darker sections */
  --bg-tertiary: #374151;           /* Hover states */
  
  /* Text */
  --text-primary: #f3f4f6;          /* Main text */
  --text-secondary: #d1d5db;        /* Secondary text */
  --text-tertiary: #9ca3af;         /* Disabled/muted */
  
  /* Borders */
  --border-color: #4b5563;          /* Element borders */
  --border-color-light: #6b7280;    /* Lighter borders */
  
  /* Layout */
  --border-radius: 0.5rem;
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md: 0 4px 6px rgba(0,0,0,0.4);
  --shadow-lg: 0 10px 15px rgba(0,0,0,0.5);
}
```

**Light Theme**:
```css
:root {
  --color-primary: #2563eb;
  --color-success: #059669;
  /* ... lighter colors ... */
}
```

### 6.4 Component Library

**Buttons**:
- `.button` - Base button
- `.button-primary` - Primary action
- `.button-secondary` - Secondary action
- `.button-danger` - Destructive action
- `.button-small` - Smaller size
- `.button-loading` - Disabled with spinner

**Cards**:
- `.card` - Base card container
- `.card-header` - Card title section
- `.card-body` - Card content
- `.card-footer` - Card action area

**Forms**:
- `.form-group` - Input + label container
- `.form-input` - Text inputs
- `.form-select` - Dropdowns
- `.form-error` - Error state
- `.form-help` - Help text

**Alerts**:
- `.alert` - Base alert
- `.alert-success` - Success message
- `.alert-danger` - Error message
- `.alert-warning` - Warning message
- `.alert-info` - Info message

### 6.5 Layout System

**Grid Container**:
```css
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 var(--spacing-md);
}
```

**Responsive Breakpoints**:
```
Mobile:  < 640px
Tablet:  640px - 1024px
Desktop: > 1024px
```

---

## 6. Technical Details

### 7.1 Database Changes

**Updated User Model**:
```python
class User(Base):
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    hashed_password = Column(String)
    display_name = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)  # NEW
    is_active = Column(Boolean, default=True)  # NEW
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**Alembic Migration**:
- Add `is_admin` and `is_active` columns to users table
- Default: is_admin=False, is_active=True
- Create index on email (for login)

### 7.2 File Structure

```
project/
├── backend/
│   ├── main.py
│   ├── plugins/
│   │   └── themes/
│   │       ├── dark_theme.py
│   │       ├── light_theme.py
│   │       └── __init__.py
│   ├── themes.py            ← Theme manager
│   └── (existing files)
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── setup.html               # NEW: First-time setup
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   ├── register.html
│   │   │   └── login-form.html
│   │   ├── projects/
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   ├── form.html
│   │   │   └── card.html
│   │   ├── models/
│   │   │   ├── list.html
│   │   │   ├── upload-form.html
│   │   │   └── card.html
│   │   ├── keys/
│   │   │   └── list.html
│   │   ├── settings/
│   │   │   └── profile.html
│   │   ├── admin/                   # NEW: Admin interface
│   │   │   ├── base.html            # Admin base template
│   │   │   ├── dashboard.html       # Admin home/overview
│   │   │   ├── users/
│   │   │   │   ├── list.html
│   │   │   │   ├── form.html        # Modal
│   │   │   │   └── card.html
│   │   │   ├── plugins/
│   │   │   │   ├── list.html
│   │   │   │   └── config.html      # Modal
│   │   │   ├── settings.html        # Global settings
│   │   │   ├── logs.html            # Log viewer
│   │   │   └── health.html          # System status
│   │   └── components/
│   │       ├── navbar.html
│   │       ├── modal.html
│   │       ├── alerts.html
│   │       ├── pagination.html
│   │       └── loading.html
│   └── static/
│       ├── css/
│       │   ├── index.css
│       │   ├── themes/
│       │   │   ├── dark.css
│       │   │   └── light.css
│       │   ├── components/
│       │   │   ├── buttons.css
│       │   │   ├── cards.css
│       │   │   ├── forms.css
│       │   │   └── alerts.css
│       │   ├── layout/
│       │   │   ├── base.css
│       │   │   ├── navbar.css
│       │   │   └── footer.css
│       │   └── utilities/
│       │       ├── spacing.css
│       │       ├── typography.css
│       │       └── responsive.css
│       ├── js/
│       │   ├── app.js        ← HTMX config & global scripts
│       │   └── theme.js      ← Theme switching logic
│       └── images/
│           └── logo.png
└── tests/
    └── integration/
        └── test_frontend_pages.py
```

### 6.2 Dependencies

**No new Python dependencies needed**:
- FastAPI already supports Jinja2 templates
- HTMX is loaded via CDN (no installation)

**CSS/Frontend**:
- HTMX (CDN)
- Bootstrap Icons (CDN) - optional
- Custom CSS (written from scratch)

### 6.3 Database

**No schema changes** - Uses existing User, Project, Model, APIKey tables

**Session Storage** - Options:
1. Server-side sessions (simple, secure) - Recommended
2. JWT tokens (already in API)
3. Database session table (overkill)

**Decision**: Use FastAPI session middleware + secure cookies

---

## 7. Extensibility & Plugin Architecture

### 7.1 Adding New Themes

**Steps** (no code changes needed to core frontend):

1. Create plugin file:
```python
# backend/plugins/themes/high_contrast_theme.py
class HighContrastTheme(ThemePlugin):
    name = "high-contrast"
    version = "1.0.0"
    css_variables = {...}
```

2. Register in `backend/plugins/themes/__init__.py`

3. Restart app (or implement hot-reload)

4. Theme appears in switcher automatically ✅

### 7.2 Adding New Pages

**Steps**:

1. Add route in `backend/main.py`:
```python
@app.get("/new-page", response_class=HTMLResponse)
async def new_page(request: Request):
    return templates.TemplateResponse("new-page.html", {"request": request})
```

2. Create template `frontend/templates/new-page.html`

3. Use CSS variables from theme system

### 7.3 Adding New Components

**Steps**:

1. Create CSS component file `frontend/static/css/components/new-component.css`

2. Use CSS variables:
```css
.new-component {
    background: var(--bg-secondary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
}
```

3. Create template partial `frontend/templates/components/new-component.html`

4. Include in parent templates with `{% include "components/new-component.html" %}`

---

## 8. Testing Strategy

### 8.1 Unit Tests

- Template rendering (Jinja2)
- Theme variable generation
- Session management
- Form validation

### 8.2 Integration Tests

- Page load and render
- Theme switching via HTMX
- Form submission via HTMX
- File upload workflow
- Authentication flows

### 8.3 Visual Testing

- Dark mode appearance
- Light mode appearance
- Responsive design (mobile, tablet, desktop)
- HTMX interactions

---

## 9. Implementation Phases

### Phase 6A: Theme System & Base Templates (T051-T055)
- Theme plugin infrastructure
- Dark and light themes
- Base template and components
- Theme switching endpoint

### Phase 6B: HTML Pages & Templates (T056-T060)
- Home/Landing page
- Authentication pages (login, register)
- Projects list and detail
- Models upload interface

### Phase 6C: HTMX Interactions (T061-T065)
- Form submissions via HTMX
- Delete confirmations
- Pagination
- Model filtering
- Real-time validation

### Phase 6D: Styling & Responsive Design (T066-T070)
- Mobile responsive layout
- Additional CSS components
- Accessibility improvements
- Cross-browser testing

### Phase 6E: Testing & Deployment (T071-T075)
- Unit tests for templates
- Integration tests for pages
- End-to-end user flow tests
- Documentation and deployment

### Phase 6F: Admin Interface (T076-T080) **NEW**
- First-time setup/bootstrap flow
- Admin dashboard and navigation
- User management interface
- Plugin manager and settings
- Logs viewer and system health

---

## 10. Admin Interface Startup Logic

### 10.1 First-Time Startup

```python
# backend/main.py startup hook

@app.on_event("startup")
async def startup_event():
    # Run database migrations
    # ...
    
    # Check if admin users exist
    admin_count = await user_service.count_where({"is_admin": True})
    
    if admin_count == 0:
        # Mark app as requiring setup
        app.state.setup_required = True
    else:
        app.state.setup_required = False
    
    logger.info(f"Setup required: {app.state.setup_required}")

# Middleware to enforce setup
@app.middleware("http")
async def setup_middleware(request: Request, call_next):
    # Allow setup and static routes
    if request.url.path in ["/setup", "/static/css", "/static/js", "/api/v1/theme/css"]:
        return await call_next(request)
    
    # If setup required and not on setup page, redirect
    if request.app.state.setup_required and request.url.path != "/setup":
        return RedirectResponse("/setup")
    
    return await call_next(request)

@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    # If already set up, redirect
    if not request.app.state.setup_required:
        return RedirectResponse("/")
    
    return templates.TemplateResponse("setup.html", {"request": request})

@app.post("/setup", response_class=HTMLResponse)
async def setup_submit(request: Request, form_data: SetupForm):
    # Validate input
    # Create admin user
    await user_service.create(
        username=form_data.username,
        email=form_data.email,
        password=form_data.password,
        is_admin=True
    )
    
    # Mark setup as complete
    request.app.state.setup_required = False
    
    # Show success message and redirect to login
    request.session["setup_complete"] = True
    return templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "message": "Admin account created! Please log in.",
            "message_type": "success"
        }
    )
```

### 10.2 Admin Route Protection

```python
# Helper to check if user is admin
async def get_admin_user(request: Request) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401)
    
    user = await user_service.get(user_id)
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return user

# Admin routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user: User = Depends(get_admin_user)):
    stats = {
        "user_count": await user_service.count(),
        "project_count": await project_service.count(),
        "model_count": await model_service.count(),
        "storage_used": await storage_service.get_used_space(),
    }
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "user": user, "stats": stats}
    )
```

---

## 11. Success Metrics

| Metric | Target | Validation |
|--------|--------|-----------|
| Page Load Time | < 500ms | Browser dev tools |
| Theme Switch | < 100ms | HTMX swap visual |
| CSS File Size | < 50KB | Uncompressed |
| JavaScript Size | < 10KB | HTMX + app.js |
| Mobile Responsive | All pages | iPhone 12 viewport |
| Accessibility | WCAG AA | Axe DevTools audit |
| Test Coverage | > 80% | pytest coverage |

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| HTMX incompatibility | Page breaks | Test all interactions |
| CSS variable unsupported | Theme fails | Polyfill or fallback |
| Session/cookie issues | Auth broken | Thorough testing |
| Mobile layout breaks | UX poor | Mobile-first CSS |

---

## 13. References

- **HTMX Docs**: https://htmx.org
- **Jinja2 Docs**: https://jinja.palletsprojects.com/
- **FastAPI Templates**: https://fastapi.tiangolo.com/advanced/templates/
- **CSS Variables**: https://developer.mozilla.org/en-US/docs/Web/CSS/--*
- **Semantic HTML**: https://www.w3.org/TR/html5/

---

---

## 14. Admin Interface Feature Summary

**New in Phase 6F**:
- ✅ First-time setup with automatic admin account creation
- ✅ Admin authentication check (is_admin flag)
- ✅ Admin dashboard with system statistics
- ✅ User management (CRUD operations)
- ✅ Plugin manager (view, enable/disable, configure)
- ✅ Global settings (theme, log level, backups)
- ✅ Real-time logs viewer with filtering
- ✅ System health and status monitoring
- ✅ Protected admin routes with proper authorization

**Ensures MVP is production-ready with**:
- Initial setup automation
- System observability
- User administration capabilities
- Plugin/configuration management

---

**Appendix**: See `tasks.md` for detailed implementation tasks and testing plan.
