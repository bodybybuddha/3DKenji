# Research & Reference: Web UI Frontend (Phase 6)

**Date**: February 21, 2026  
**Focus**: FastAPI + Jinja2 + HTMX Frontend Architecture  

---

## 1. Technology Stack Research

### 1.1 FastAPI + Jinja2 Templates

**Why Jinja2 over other templates?**
- Default in FastAPI
- Server-side rendering (simpler than SPA)
- User already familiar with it (Flask background)
- Perfect for progressive enhancement with HTMX
- No build step required

**FastAPI Template Integration**:
```python
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="frontend/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
```

**Key Features**:
- `request` object required in context
- Template inheritance with `extends`
- Template includes with `include`
- Filters and macros available
- Auto-escaping for security

**References**:
- FastAPI Templates: https://fastapi.tiangolo.com/advanced/templates/
- Jinja2 Docs: https://jinja.palletsprojects.com/
- Real Python Jinja2: https://realpython.com/primer-on-jinja-templating/

---

### 1.2 HTMX for Interactivity

**Why HTMX over Vue/React?**
- No build step or Node.js dependency
- HTML-powered interactivity (HTML is the model)
- Works with any backend
- Minimal JavaScript needed
- Progressive enhancement (works without JS)
- Smaller file size (13 KB minified)
- Server-side decisions stay server-side

**Common HTMX Patterns**:

```html
<!-- Form submission without page reload -->
<form hx-post="/submit" hx-target="#result">
  <input name="field" required>
  <button type="submit">Submit</button>
</form>
<div id="result"></div>

<!-- Delete with confirmation -->
<button hx-delete="/api/item/1"
        hx-confirm="Delete this item?"
        hx-target="closest .item"
        hx-swap="outerHTML swap:1s">Delete</button>

<!-- Click to load more -->
<button hx-get="/items?skip=10" 
        hx-target="#items"
        hx-swap="beforeend">Load More</button>

<!-- Search as you type -->
<input type="text" 
       hx-get="/search" 
       hx-trigger="keyup delay:500ms"
       hx-target="#results">

<!-- Polling (auto-refresh every 3s) -->
<div hx-get="/api/status" hx-trigger="every 3s">
  Status: <span id="status">Loading...</span>
</div>
```

**HTMX Attributes Cheat Sheet**:
- `hx-get="/path"` - Make GET request
- `hx-post="/path"` - Make POST request
- `hx-put=/path"` - Make PUT request
- `hx-delete="/path"` - Make DELETE request
- `hx-target="#id"` - Where to insert response
- `hx-swap="innerHTML"` - How to insert (innerHTML, outerHTML, beforeend, afterbegin, etc.)
- `hx-confirm="message"` - Show confirmation before request
- `hx-trigger="click"` - What triggers request (click, change, keyup, etc.)
- `hx-boost="true"` - Boost all links/forms on page
- `hx-request` - Custom code on request
- `hx-prompt="message"` - Prompt user for input

**Response Requirements**:
- For form submission: Return HTML fragment to insert
- For deletion: Return empty or element to replace
- For errors: Return HTML with error message, keep form in DOM
- For success: Return updated element or full page section

**References**:
- HTMX Official: https://htmx.org
- HTMX API Reference: https://htmx.org/reference/
- HTMX Essays: https://htmx.org/essays/ (great for understanding philosophy)
- Example App: https://github.com/bigskysoftware/htmx/tree/master/www

---

### 1.3 CSS Variables for Theming

**Why CSS Variables?**
- Dynamic color switching without recompiling CSS
- No JavaScript needed for theme switching
- Browser support: All modern browsers (99%+)
- Performance: Minimal overhead
- Maintainability: All colors in one place
- No color values in HTML/JavaScript code

**CSS Variables Syntax**:

```css
/* Define variables */
:root {
  --color-primary: #3b82f6;
  --color-secondary: #6b7280;
  --space-sm: 0.5rem;
  --space-md: 1rem;
}

/* Use variables */
.button {
  background: var(--color-primary);
  padding: var(--space-md);
}

/* Fallback for older browsers */
.button {
  background: var(--color-primary, #3b82f6);
}

/* Change theme by updating :root */
[data-theme="light"] {
  --color-primary: #2563eb;
  --color-secondary: #4b5563;
}

/* Or load different stylesheet */
<link rel="stylesheet" href="/api/v1/theme/css/dark">
```

**Browser Support**:
- Chrome 49+ (2015)
- Firefox 31+ (2014)
- Safari 9.1+ (2016)
- Edge 15+ (2017)
- All modern browsers ✅

**Performance**:
- No CSS-in-JS parsing overhead
- No runtime style compilation
- Instant theme switching
- No FOUC (Flash of Unstyled Content) if CSS loaded properly

**References**:
- MDN CSS Variables: https://developer.mozilla.org/en-US/docs/Web/CSS/--*
- CSS-Tricks Guide: https://css-tricks.com/difference-between-types-of-css-variables/
- Theming with CSS Variables: https://www.smashingmagazine.com/2018/05/css-custom-properties-strategy-guide/

---

### 1.4 Session Management in FastAPI

**JWT vs Sessions for Web UI**:

| Aspect | JWT | Sessions |
|--------|-----|----------|
| Storage | Client (cookie) | Server |
| Stateless | Yes | No |
| Backend scalability | Better (no state) | Needs shared storage |
| Security | Token revocation hard | Easy to revoke |
| CSRF | Vulnerable | Protected by SameSite |
| Page rendering | Need to pass token | Automatic in context |

**Decision for Web UI**: Use sessions + cookies
- Server renders HTML (can access session directly)
- No need to pass JWT to frontend
- Simpler implementation
- Keep JWT API for third-party clients

**Implementation**:
```python
from fastapi.middleware import Middleware
from fastapi.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret")

@app.post("/login")
async def login(request: Request, credentials: LoginRequest):
    # Validate credentials...
    request.session["user_id"] = user.id
    return templates.TemplateResponse("success.html", {"request": request})

@app.get("/dashboard")
async def dashboard(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login")
    return templates.TemplateResponse("dashboard.html", {"request": request})
```

**References**:
- FastAPI Sessions: https://fastapi.tiangolo.com/advanced/middleware/
- Session Best Practices: https://owasp.org/www-community/attacks/Session_fixation

---

## 2. Design System Research

### 2.1 Color Theory for Themes

**Dark Mode Best Practices**:
- Don't use pure black (#000000) - it's too harsh
- Use dark gray (#1f2937, #111827) - easier on eyes
- Maintain contrast ratios: 4.5:1 for AA, 7:1 for AAA
- Avoid pure white text - use off-white (#f3f4f6)
- Use accent colors that pop against dark background

**Light Mode Best Practices**:
- Clean white or near-white background (#ffffff, #f9fafb)
- Dark gray/black text (#111827, #374151)
- Soft shadows from brightness difference
- Accent colors should be darker than dark mode equivalent

**Testing Colors**:
- Tool: https://www.tpaui.com/the-color-contrast-accessibility-tool/
- Tool: https://contrast-ratio.com/
- Check contrast for normal text and large text separately

**References**:
- Material Design Dark Theme: https://material.io/design/color/dark-theme.html
- Web Accessibility WCAG Colors: https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html

---

### 2.2 Responsive Design Patterns

**Mobile-First Approach**:
- Start with mobile styles (narrow viewport)
- Use media queries to add styles for larger screens
- Always works even if CSS not fully loaded
- Better performance on mobile

**Breakpoints Convention**:
```
Mobile:  < 640px   (iPhone, small tablets)
Tablet:  640-1024px (iPad, medium screens)
Desktop: > 1024px  (desktop, large monitors)

CSS Media Query:
@media (min-width: 640px) { /* tablet styles */ }
@media (min-width: 1024px) { /* desktop styles */ }
```

**Common Responsive Patterns**:
- Single column → 2 columns → 3+ columns (grid)
- Hamburger menu → horizontal nav (flex/grid)
- Full width inputs → side-by-side (grid/flex)
- Stacked cards → grid layout

**References**:
- Mobile-First Responsive Guide: https://www.nngroup.com/articles/mobile-first-responsive-web-design/
- Responsive Design Basics: https://web.dev/responsive-web-design-basics/

---

### 2.3 Accessibility Standards (WCAG 2.1)

**Key Standards for Web UI**:

| Level | Standard | Example |
|-------|----------|---------|
| A | Minimum requirement | Large text, alt text |
| AA | Standard (target for us) | 4.5:1 color contrast, ARIA labels |
| AAA | Enhanced (nice to have) | 7:1 color contrast, detailed alt text |

**Critical WCAG AA Items**:
1. **Color Contrast** (4.5:1 ratio minimum)
   - Use contrast checker tools
   - Test both normal and large text
2. **Keyboard Navigation**
   - Tab through all interactive elements
   - Focus indicators visible
   - No keyboard traps
3. **ARIA Labels**
   - `aria-label` for icon buttons
   - `aria-live` for dynamic content
   - `aria-describedby` for error messages
4. **Semantic HTML**
   - Use `<button>` not `<div>` styled as button
   - Use `<nav>`, `<main>`, `<form>`, `<label>`
   - Proper heading hierarchy (h1, h2, h3)
5. **Form Accessibility**
   - Labels associated with inputs
   - Required fields marked
   - Error messages clear
   - Help text available

**Testing Tools**:
- axe DevTools: https://www.deque.com/axe/devtools/
- WAVE Browser Extension: https://wave.webaim.org/extension/
- Lighthouse in Chrome DevTools
- Manual keyboard testing

**References**:
- WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- WebAIM: https://webaim.org/

---

## 3. Code Examples

### 3.1 Complete HTMX Form Example

**Backend (FastAPI)**:
```python
@app.post("/projects/create")
async def create_project(
    request: Request,
    title: str = Form(...),
    description: str = Form(None)
):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse("/login")
    
    # Create project
    project = await project_service.create(user_id, title, description)
    
    # Return HTML fragment for new project card
    return templates.TemplateResponse(
        "projects/card.html",
        {"request": request, "project": project},
        status_code=201  # HTMX recognizes this
    )
```

**Frontend (Template)**:
```html
<!-- projects/list.html -->
<div class="projects-grid" id="projects-list">
  {% for project in projects %}
  {% include "projects/card.html" %}
  {% endfor %}
</div>

<form hx-post="/projects/create"
      hx-target="#projects-list"
      hx-swap="beforeend"
      hx-on::after-request="if(event.detail.xhr.status==201) this.reset()">
  <div class="form-group">
    <label for="title">Project Title</label>
    <input type="text" id="title" name="title" required>
  </div>
  
  <div class="form-group">
    <label for="description">Description</label>
    <textarea id="description" name="description"></textarea>
  </div>
  
  <button type="submit">Create Project</button>
</form>

<!-- projects/card.html component -->
<div class="card project-card" hx-target="this">
  <h3>{{ project.title }}</h3>
  <p>{{ project.description }}</p>
  <div class="actions">
    <button hx-delete="/api/v1/projects/{{ project.id }}"
            hx-confirm="Delete this project?"
            hx-swap="outerHTML swap:1s">Delete</button>
  </div>
</div>
```

---

### 3.2 Theme Plugin Example

**Backend (Python)**:
```python
# backend/plugins/themes/custom_theme.py

from backend.core.plugin_interfaces import ThemePlugin

class CustomTheme(ThemePlugin):
    """Your custom company theme"""
    
    name = "custom"
    version = "1.0.0"
    is_default = False
    
    css_variables = {
        # Brand colors (from company style guide)
        "color-primary": "#0066cc",      # Company blue
        "color-success": "#008000",      # Forest green
        "color-danger": "#cc0000",       # Ruby red
        "color-warning": "#ff9900",      # Safety orange
        "color-info": "#0099ff",         # Sky blue
        
        # Custom backgrounds
        "bg-primary": "#f8f9fa",         # Light gray
        "bg-secondary": "#ffffff",       # White
        "bg-tertiary": "#e9ecef",        # Medium gray
        
        # ... rest of variables
    }
    
    async def get_css(self) -> str:
        """Generate CSS with theme variables"""
        css = ":root {\n"
        for key, value in self.css_variables.items():
            css += f"  --{key}: {value};\n"
        css += "}\n"
        return css
```

**Register Plugin**:
```python
# backend/plugins/themes/__init__.py

from .dark_theme import DarkTheme
from .light_theme import LightTheme
from .custom_theme import CustomTheme  # New!

__all__ = ["DarkTheme", "LightTheme", "CustomTheme"]
```

**Use in Template**:
```html
<!-- frontend/templates/base.html -->
<head>
    <!-- Theme CSS from API (any registered theme) -->
    <link rel="stylesheet" href="/api/v1/theme/css/{{ current_theme }}">
    
    <!-- Component styles (use theme variables) -->
    <link rel="stylesheet" href="/static/css/components.css">
</head>

<select name="theme" 
        hx-get="/api/v1/theme/switch" 
        hx-target="body" 
        hx-swap="outerHTML">
    <option value="dark" {% if current_theme == 'dark' %}selected{% endif %}>Dark</option>
    <option value="light" {% if current_theme == 'light' %}selected{% endif %}>Light</option>
    <option value="custom" {% if current_theme == 'custom' %}selected{% endif %}>Custom</option>
</select>
```

---

## 4. File Upload Best Practices

### 4.1 Client-Side Validation

```html
<form hx-post="/projects/{{ project_id }}/models"
      enctype="multipart/form-data"
      hx-trigger="change from:#file-input"
      hx-on="htmx:xhr:progress(loaded(detail.loaded), total(detail.loaded))">
  
  <input type="file" 
         id="file-input"
         name="file"
         accept=".stl,.3mf,.obj,.gcode"
         required>
  
  <div id="upload-error" style="display:none" class="alert alert-danger"></div>
  
  <progress id="progress" value="0" max="100" style="display:none"></progress>
  
  <button type="submit">Upload</button>
</form>

<script>
document.getElementById('file-input').addEventListener('change', (e) => {
  const file = e.target.files[0];
  const maxSize = 10 * 1024 * 1024; // 10MB
  const validTypes = ['.stl', '.3mf', '.obj', '.gcode'];
  const ext = '.' + file.name.split('.').pop().toLowerCase();
  
  // Client-side validation
  if (!validTypes.includes(ext)) {
    document.getElementById('upload-error').textContent = 
      'Invalid file type. Use: .stl, .3mf, .obj, .gcode';
    document.getElementById('upload-error').style.display = 'block';
    return;
  }
  
  if (file.size > maxSize) {
    document.getElementById('upload-error').textContent = 
      'File too large. Maximum 10MB.';
    document.getElementById('upload-error').style.display = 'block';
    return;
  }
  
  document.getElementById('upload-error').style.display = 'none';
  document.getElementById('progress').style.display = 'block';
  
  // Let HTMX handle the upload
  htmx.ajax('POST', e.target.parentElement.getAttribute('hx-post'), {
    body: new FormData(e.target.parentElement)
  });
});
</script>
```

---

## 5. Testing Strategy

### 5.1 Unit Testing Templates

```python
# tests/unit/test_templates.py

from fastapi.testclient import TestClient
from jinja2 import Environment, FileSystemLoader

def test_base_template_renders():
    """Test base template renders without errors"""
    env = Environment(loader=FileSystemLoader('frontend/templates'))
    template = env.get_template('base.html')
    
    html = template.render(
        request=MockRequest(),
        current_theme='dark',
        user=None
    )
    
    assert '<html' in html
    assert '__title__' in html or 'block title' in str(template.source)

def test_project_card_renders():
    """Test project card renders with data"""
    env = Environment(loader=FileSystemLoader('frontend/templates'))
    template = env.get_template('projects/card.html')
    
    html = template.render(
        request=MockRequest(),
        project={'id': 1, 'title': 'Test', 'description': 'Desc'}
    )
    
    assert 'Test' in html
    assert 'Desc' in html
```

### 5.2 Integration Testing Pages

```python
# tests/integration/test_frontend_pages.py

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_home_page_unauthenticated():
    """Test home page loads without authentication"""
    response = client.get("/")
    assert response.status_code == 200
    assert "<html" in response.text
    assert "3DKenji" in response.text

def test_projects_page_authenticated():
    """Test projects page with authenticated user"""
    # Create test user and session
    response = client.post("/login", data={
        "username": "testuser",
        "password": "password123"
    })
    
    # Session cookie should be set
    assert "session" in client.cookies
    
    # Access projects page
    response = client.get("/projects")
    assert response.status_code == 200

def test_projects_page_unauthenticated():
    """Test projects page redirects without auth"""
    response = client.get("/projects", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["location"]
```

---

## 6. Performance Optimization

### 6.1 CSS Optimization

```css
/* ✅ Good: Use CSS variables */
button {
  background: var(--color-primary);
}

/* ❌ Avoid: Hardcoded colors that need theme support */
button {
  background: #3b82f6;
}

/* ✅ Good: One CSS file with all variables */
@import url('/api/v1/theme/css/dark');
@import url('/static/css/components.css');

/* ❌ Avoid: Multiple files or inline styles */
<style>button { background: #3b82f6; }</style>
```

### 6.2 HTMX Performance

```html
<!-- ✅ Good: Efficient swap -->
<form hx-post="/submit"
      hx-target="#result"
      hx-swap="innerHTML">  <!-- Only replace content, not whole element -->

<!-- ❌ Avoid: Inefficient swaps -->
<form hx-post="/submit"
      hx-target="body"
      hx-swap="outerHTML">  <!-- Replaces entire page -->
```

---

## 7. References & Resources

### Official Documentation
- HTMX: https://htmx.org
- FastAPI: https://fastapi.tiangolo.com
- Jinja2: https://jinja.palletsprojects.com
- MDN Web Docs: https://developer.mozilla.org

### Tutorials & Guides
- Real Python FastAPI: https://realpython.com/fastapi-python-web-apis/
- HTMX Essays: https://htmx.org/essays/
- CSS Variables Guide: https://css-tricks.com/difference-between-types-of-css-variables/

### Tools
- Contrast Checker: https://contrast-ratio.com/
- WAVE Accessibility: https://wave.webaim.org/
- Lighthouse: Built into Chrome DevTools
- axe DevTools: https://www.deque.com/axe/devtools/

---

**Last Updated**: February 21, 2026  
**Next Review**: After Phase 6 completion  
