# Task Breakdown: Phase 6 - Web UI Frontend

**Total Tasks**: 30 (T051-T080)  
**Estimated Duration**: 3 weeks (15 working days)  
**Sprint Schedule**: Feb 24 - Mar 11, 2026  

---

## Status Update (Feb 21, 2026)

**Completed**:
- Phase 6A: Theme system + plugins + base templates
- Phase 6B: Auth, projects, keys, settings, admin templates
- Phase 6C: HTMX interactions + fragments
- Phase 6D: Styling + responsive layout (base CSS system)
- Phase 6E: Form validation (client + server)

**Partially complete**:
- Phase 6F: Admin interface (pages + endpoints done; setup flow and admin auth checks pending)

---

## Phase 6A: Theme System & Base Templates (T051-T055)

### T051: Create Theme Plugin Infrastructure ⭕

**Objective**: Extend plugin system to support themes

**Tasks**:
- [ ] Add `ThemePlugin` base class to `backend/core/plugin_interfaces.py`
  - Properties: `name`, `version`, `is_default`, `css_variables`
  - Method: `async get_css() -> str`
- [ ] Create `backend/themes.py` with `ThemeManager` class
  - `get_theme(name: str)` - Get theme by name
  - `list_themes()` - List all available themes
  - `get_default_theme()` - Return dark theme
- [ ] Add theme discovery to `PluginManager` if not already present
- [ ] Update `backend/core/plugin_interfaces.py` docstring with ThemePlugin example

**Deliverables**:
- ✅ `backend/themes.py` - 100+ lines
- ✅ `backend/core/plugin_interfaces.py` - Updated with ThemePlugin

**Testing**:
- [ ] Unit test: `tests/unit/test_theme_manager.py`
  - Test theme loading
  - Test default theme selection
  - Test theme listing

**Dependencies**: None (extends existing system)

---

### T052: Implement Dark Theme Plugin ⭕

**Objective**: Create default dark theme with CSS variable definitions

**Tasks**:
- [ ] Create `backend/plugins/themes/dark_theme.py`
  - Implement `DarkTheme` class with `css_variables` dict
  - Include all semantic colors, backgrounds, text colors, borders, shadows
  - Implement `get_css()` method to generate CSS from variables
- [ ] Define complete color palette:
  - Semantic: primary (#3b82f6), success (#10b981), danger (#ef4444), warning (#f59e0b), info (#0ea5e9)
  - Backgrounds: primary (#1f2937), secondary (#111827), tertiary (#374151)
  - Text: primary (#f3f4f6), secondary (#d1d5db), tertiary (#9ca3af)
  - Borders: color (#4b5563), color-light (#6b7280)
  - Spacing and shadows
- [ ] Mark as `is_default = True`
- [ ] Register in `backend/plugins/themes/__init__.py`

**Deliverables**:
- ✅ `backend/plugins/themes/dark_theme.py` - 150 lines
- ✅ `backend/plugins/themes/__init__.py` - Updated

**Testing**:
- [ ] Verify `get_css()` generates valid CSS
- [ ] Test all color variables are present

**Dependencies**: T051

---

### T053: Implement Light Theme Plugin ⭕

**Objective**: Create light theme variant

**Tasks**:
- [ ] Create `backend/plugins/themes/light_theme.py`
  - Implement `LightTheme` class
  - Define lighter color variants of dark theme:
    - Semantic: primary (#2563eb), success (#059669), danger (#dc2626), warning (#d97706), info (#0284c7)
    - Backgrounds: primary (#ffffff), secondary (#f9fafb), tertiary (#f3f4f6)
    - Text: primary (#111827), secondary (#374151), tertiary (#6b7280)
    - Borders: color (#e5e7eb), color-light (#f0f0f0)
  - Shadows: lighter values (0.05-0.1 opacity instead of 0.3-0.5)
- [ ] Mark as `is_default = False`
- [ ] Register in `backend/plugins/themes/__init__.py`
- [ ] Ensure logo/images work on light background

**Deliverables**:
- ✅ `backend/plugins/themes/light_theme.py` - 150 lines
- ✅ Updated theme registration

**Testing**:
- [ ] Verify `get_css()` generates valid CSS
- [ ] All color variables defined
- [ ] Colors have adequate contrast for accessibility

**Dependencies**: T051, T052

---

### T054: Add Theme API Endpoints ⭕

**Objective**: Create FastAPI routes for theme management

**Tasks**:
- [ ] Add to `backend/main.py`:
  - `GET /api/v1/theme/css/{theme_name}` - Return CSS for theme
    - Returns CSS as `text/css` mimetype
    - Sets `X-Theme` response header
  - `GET /api/v1/themes` - List available themes
    - Returns JSON: `{ "themes": [{ "name": "dark", "default": true }, ...] }`
  - `GET /api/v1/theme/switch` - Switch theme and return updated HTML
    - Takes `theme` query parameter
    - Returns full HTML page with new theme applied
    - Sets X-Theme header for client-side detection
- [ ] Add theme manager instance: `theme_manager = ThemeManager()`
- [ ] All routes use `StreamingResponse` for CSS delivery

**Deliverables**:
- ✅ `backend/main.py` - Updated with theme routes (~50 lines added)

**Testing**:
- [ ] Integration test: `tests/integration/test_theme_endpoints.py`
  - Test GET /api/v1/themes returns available themes
  - Test GET /api/v1/theme/css/dark returns CSS
  - Test GET /api/v1/theme/css/light returns CSS
  - Test CSS contains all color variables
  - Test invalid theme returns 404
  - Test X-Theme header present in response

**Dependencies**: T051, T052, T053

---

### T055: Create Base Template Structure ⭕

**Objective**: Build base Jinja2 template with theme system integration

**Tasks**:
- [ ] Create `frontend/templates/base.html`
  - DOCTYPE, html, head setup
  - Meta tags (charset, viewport, description)
  - Dynamic theme CSS loading: `<link rel="stylesheet" href="/api/v1/theme/css/{{ current_theme }}">`
  - Static CSS includes (components, layout, utilities)
  - Include HTMX from CDN
  - Support for page title via `{% block title %}`
  - Main navigation component include
  - Main content block: `{% block content %}`
  - Footer section with theme switcher
  - JavaScript for theme persistence (localStorage)
- [ ] Create `frontend/templates/components/navbar.html`
  - Logo and home link
  - Navigation menu items
  - User menu dropdown (with login/logout)
  - Theme switcher: `<select hx-get="/api/v1/theme/switch">`
- [ ] Create `frontend/templates/components/footer.html`
  - Simple footer with copyright
  - Link to documentation
  - Link to GitHub

**Deliverables**:
- ✅ `frontend/templates/base.html` - 80 lines
- ✅ `frontend/templates/components/navbar.html` - 40 lines
- ✅ `frontend/templates/components/footer.html` - 20 lines

**Testing**:
- [ ] Manual: Load home page, verify dark theme applied
- [ ] Manual: Change to light theme, verify style changes
- [ ] Manual: Refresh page, verify theme preference persists
- [ ] Manual: Check navbar and footer render

**Dependencies**: T054

---

## Phase 6B: HTML Pages & Templates (T056-T060)

### T056: Create Home & Landing Pages ⭕

**Objective**: Build public-facing home page and feature overview

**Tasks**:
- [ ] Create `frontend/templates/index.html`
  - Hero section with 3DKenji branding
  - Feature highlights (Projects, Models, API Keys, Health monitoring)
  - Call-to-action buttons: "Register" and "Login"
  - Feature cards with icons
  - Quick links to documentation
  - Extends base.html
- [ ] Verify responsive layout (mobile-first)
- [ ] Add route to `backend/main.py`:
  - `GET /` - Serve index.html
  - Requires: `from fastapi.responses import HTMLResponse`

**Deliverables**:
- ✅ `frontend/templates/index.html` - 100 lines

**Testing**:
- [ ] Manual: Home page loads
- [ ] Manual: Theme switching works on home page
- [ ] Manual: Responsive on mobile, tablet, desktop
- [ ] Manual: All links work

**Dependencies**: T055

---

### T057: Create Authentication Pages ⭕

**Objective**: Build login and registration pages

**Tasks**:
- [ ] Create `frontend/templates/auth/login.html`
  - Form with username and password fields
  - "Not registered?" link to register page
  - "Forgot password?" placeholder link (future)
  - Submit button
  - Extends base.html
- [ ] Create `frontend/templates/auth/register.html`
  - Form: username, email, password, display_name
  - Password requirements text
  - "Already registered?" link to login
  - Submit button
  - Extends base.html
- [ ] Create `frontend/templates/auth/login-form.html` (component for reuse)
  - Actual form HTML (shared between pages)
- [ ] Add routes to `backend/main.py`:
  - `GET /login` - Serve login.html
  - `POST /login` - Accept form submission, validate, set session cookie, redirect
  - `GET /register` - Serve register.html
  - `POST /register` - Accept form submission, create user, set session, redirect
  - `GET /logout` - Clear session, redirect
- [ ] Add session middleware to FastAPI app

**Deliverables**:
- ✅ `frontend/templates/auth/login.html` - 50 lines
- ✅ `frontend/templates/auth/register.html` - 60 lines
- ✅ `frontend/templates/auth/login-form.html` - 20 lines
- ✅ `backend/main.py` - Updated with auth routes (~100 lines)

**Testing**:
- [ ] Manual: Register new user via form
- [ ] Manual: Login with created user
- [ ] Manual: Logout clears session
- [ ] Manual: Protected pages redirect to login when not authenticated
- [ ] Manual: Forms show validation errors
- [ ] Manual: Theme switching works on auth pages

**Dependencies**: T056

---

### T058: Create Projects Pages ⭕

**Objective**: Build project listing and detail pages

**Tasks**:
- [ ] Create `frontend/templates/projects/list.html`
  - Extends base.html
  - "Create Project" button (opens modal)
  - Grid/list of project cards
  - Each card shows: title, description, model count, created date
  - Card has: View, Edit, Delete buttons
  - Pagination controls (if > 10 projects)
  - Empty state message if no projects
- [ ] Create `frontend/templates/projects/card.html` (component)
  - Reusable project card
- [ ] Create `frontend/templates/projects/detail.html`
  - Project title, description, metadata
  - Edit button (opens modal)
  - Delete button (with confirmation)
  - "Upload Model" section
  - Models list (see T059)
  - Back to projects link
- [ ] Create `frontend/templates/projects/form.html` (modal component)
  - Form for create/edit project
  - Fields: title (required), description (optional)
  - Metdata/tags field (optional JSON editor or simple textarea)
  - Submit button
- [ ] Add routes to `backend/main.py`:
  - `GET /projects` - List projects page (requires auth)
  - `GET /projects/<id>` - Project detail page
  - Form submission routes handle validation and redirect or return modal response

**Deliverables**:
- ✅ `frontend/templates/projects/list.html` - 80 lines
- ✅ `frontend/templates/projects/detail.html` - 100 lines
- ✅ `frontend/templates/projects/card.html` - 30 lines
- ✅ `frontend/templates/projects/form.html` - 40 lines
- ✅ `backend/main.py` - Updated (~80 lines)

**Testing**:
- [ ] Manual: List projects page loads
- [ ] Manual: Pagination works
- [ ] Manual: Create project via modal (HTMX)
- [ ] Manual: Edit project via modal
- [ ] Manual: Delete project with confirmation
- [ ] Manual: Theme switching on project pages

**Dependencies**: T057

---

### T059: Create Models Upload & List Pages ⭕

**Objective**: Build 3D model management interface

**Tasks**:
- [ ] Create `frontend/templates/models/upload-form.html` (component)
  - File input (accept=".stl,.3mf,.obj,.gcode")
  - Optional: tags input (comma-separated)
  - Optional: metadata textarea (JSON)
  - Progress bar for upload
  - Submit button
  - File size validation message (max 10MB)
- [ ] Create `frontend/templates/models/list.html`
  - Display in project detail page (include models listing)
  - Table or grid view
  - Each model: filename, size, type, upload date, tags
  - Download/view button (future)
  - Delete button with confirmation
- [ ] Create `frontend/templates/models/card.html` (component)
  - Reusable model card for grid view
- [ ] Add routes to `backend/main.py`:
  - `POST /projects/<id>/models` - Handle multipart file upload
    - Validates file type and size
    - Calls storage backend
    - Returns updated models list (HTMX partial)
  - `DELETE /api/v1/models/<id>` - Delete model (already exists)
- [ ] Add file upload progress indicator (HTMX with hx-trigger)

**Deliverables**:
- ✅ `frontend/templates/models/upload-form.html` - 40 lines
- ✅ `frontend/templates/models/list.html` - 60 lines
- ✅ `frontend/templates/models/card.html` - 25 lines
- ✅ `backend/main.py` - Updated with model routes (~50 lines)

**Testing**:
- [ ] Manual: Upload valid model file
- [ ] Manual: Reject invalid file type (not .stl/.3mf/.obj/.gcode)
- [ ] Manual: Reject oversized file (> 10MB)
- [ ] Manual: File appears in list after upload
- [ ] Manual: Delete model with confirmation
- [ ] Manual: Progress indicator shows during upload
- [ ] Manual: Theme switching works

**Dependencies**: T058

---

### T060: Create API Keys & Settings Pages ⭕

**Objective**: Build API key management and user settings

**Tasks**:
- [ ] Create `frontend/templates/keys/list.html`
  - Table of user's API keys
  - Each row: name, created date, last used date (if available)
  - Copy button for key ID
  - Delete/Revoke button with confirmation
  - "Create New Key" button (opens form)
- [ ] Create `frontend/templates/keys/form.html` (modal component)
  - Input: key name (required)
  - Input: scopes/permissions (future - for now just full access)
  - Submit button
  - On success, show secret once: "Copy secret now, it won't be shown again!"
- [ ] Create `frontend/templates/settings/profile.html`
  - Display user info: username, email, display_name, member since
  - Edit button for profile (opens modal)
  - Change password section
  - Delete account button (with serious warning)
- [ ] Add routes to `backend/main.py`:
  - `GET /keys` - API keys page
  - `GET /settings` - Settings/profile page
  - `POST /settings/edit` - Update profile (HTMX)
  - `POST /settings/password` - Change password (HTMX)
- [ ] Add API key endpoint previously implemented to form

**Deliverables**:
- ✅ `frontend/templates/keys/list.html` - 70 lines
- ✅ `frontend/templates/keys/form.html` - 35 lines
- ✅ `frontend/templates/settings/profile.html` - 80 lines
- ✅ `backend/main.py` - Updated (~70 lines)

**Testing**:
- [ ] Manual: View API keys page
- [ ] Manual: Create new API key, secret shown once
- [ ] Manual: Copy secret to clipboard
- [ ] Manual: Revoke API key with confirmation
- [ ] Manual: View settings/profile page
- [ ] Manual: Edit profile via modal
- [ ] Manual: Change password

**Dependencies**: T058

---

## Phase 6C: HTMX Interactions & Dynamic Updates (T061-T065)

### T061: Implement Form Submissions via HTMX ⭕

**Objective**: Convert form submissions to HTMX for seamless UX

**Tasks**:
- [ ] Update all forms to use HTMX attributes:
  - `hx-post="/api/endpoint"` for creation/updates
  - `hx-target="#target-element"` for where to insert response
  - `hx-swap="outerHTML"` or `beforeend` depending on context
  - `hx-confirm="Are you sure?"` for destructive actions
  - Examples:
    - Project create: `hx-post="/projects/create" hx-target="#projects-list" hx-swap="beforeend"`
    - Project edit: `hx-post="/projects/123/edit" hx-target="#project-card-123" hx-swap="outerHTML"`
    - Model upload: Multipart form with progress
- [ ] Update backend routes to return HTML partials when HTMX request:
  - Check for `HX-Request` header
  - Return just the updated component, not full page
  - Set appropriate status codes (201 for create, 200 for update, 204 for delete)
- [ ] Add loading spinner during submissions
- [ ] Add success/error messages after submission
- [ ] Validation errors display in form without page reload

**Deliverables**:
- ✅ All templates updated with HTMX attributes
- ✅ `backend/main.py` - Updated routes to handle HTMX requests (~100 lines)
- ✅ `frontend/static/js/app.js` - HTMX configuration and helpers

**Testing**:
- [ ] Manual: Create project via form (no page reload)
- [ ] Manual: Edit project via form (no page reload)
- [ ] Manual: Upload model (no page reload)
- [ ] Manual: Form validation errors display
- [ ] Manual: Success messages appear
- [ ] Manual: All HTMX interactions work

**Dependencies**: T056-T060

---

### T062: Implement Delete Confirmations with HTMX ⭕

**Objective**: Add destructive action confirmations

**Tasks**:
- [ ] Add `hx-confirm` attribute to all delete buttons
  - Example: `<button hx-delete="/api/v1/projects/123" hx-confirm="Delete project 'Benchy'? This cannot be undone.">Delete</button>`
- [ ] HTMX will show browser confirm dialog before sending request
- [ ] If user cancels, request not sent
- [ ] If user confirms, request sent and element removed
- [ ] Test with all delete operations:
  - Delete project
  - Delete model
  - Revoke API key
  - Delete account

**Deliverables**:
- ✅ All delete buttons updated with hx-confirm

**Testing**:
- [ ] Manual: Click delete, see confirmation dialog
- [ ] Manual: Cancel confirmation, request not sent
- [ ] Manual: Confirm deletion, element removes from page
- [ ] Manual: Test on all delete operations

**Dependencies**: T061

---

### T063: Implement Pagination with HTMX ⭕

**Objective**: Load pages without full page refresh

**Tasks**:
- [ ] Create `frontend/templates/components/pagination.html`
  - Previous/Next buttons
  - Page number buttons
  - Uses `hx-get="/projects?skip={}&limit={}"` to fetch next page
  - `hx-target="#projects-list"`
  - `hx-swap="innerHTML"` to replace list content
- [ ] Update list pages (projects, models, keys) with pagination component
- [ ] Backend already supports `skip` and `limit` parameters
- [ ] Show "X of Y items" indicator
- [ ] Disable prev/next buttons at boundaries

**Deliverables**:
- ✅ `frontend/templates/components/pagination.html` - 30 lines
- ✅ Updated list templates to include pagination

**Testing**:
- [ ] Manual: Projects list with > 10 items shows pagination
- [ ] Manual: Click next page, list updates without reload
- [ ] Manual: Page numbers reflect current page
- [ ] Manual: Previous/next buttons disabled appropriately

**Dependencies**: T058

---

### T064: Implement Search & Filtering with HTMX ⭕

**Objective**: Real-time search without page refresh

**Tasks**:
- [ ] Add search input to projects and models lists:
  - `<input name="search" hx-get="/projects/search" hx-target="#results" hx-trigger="keyup delay:500ms">`
- [ ] Backend routes:
  - `GET /projects/search?q=query` - Search projects by title/description
  - Returns filtered project list (HTML partial)
- [ ] Add filter dropdowns (future - for now just search)
- [ ] Show "No results" message if no matches
- [ ] Maintain pagination with search results

**Deliverables**:
- ✅ Search input on projects and models lists
- ✅ `backend/main.py` - Add search routes (~40 lines)
- ✅ Backend filters by title using case-insensitive query

**Testing**:
- [ ] Manual: Type in search, results filter in real-time
- [ ] Manual: Clear search, all projects return
- [ ] Manual: Search works on models list too
- [ ] Manual: No results message appears when appropriate

**Dependencies**: T058, T063

---

### T065: Implement Modal Dialogs with HTMX ⭕

**Objective**: In-page modals for forms without navigation

**Tasks**:
- [ ] Create `frontend/templates/components/modal.html`
  - Container div with semi-transparent backdrop
  - Close button (X icon)
  - `{% block modal_content %}`
- [ ] Create `frontend/static/js/modal.js`
  - Show/hide modal functions
  - Close on backdrop click
  - Keyboard escape to close
- [ ] Add "Create Project" button with `hx-get="/projects/form" hx-target="#modal"`
  - Opens form in modal
  - Submit in modal posts to backend
  - Backend returns success/error response
  - Modal closes on success
- [ ] Apply to all create/edit operations:
  - Create project
  - Edit project
  - Create/manage API keys
  - Edit profile
- [ ] Modal shows loading state during submission

**Deliverables**:
- ✅ `frontend/templates/components/modal.html` - 25 lines
- ✅ `frontend/static/js/modal.js` - 50 lines
- ✅ Updated templates with modal buttons

**Testing**:
- [ ] Manual: Click button, modal appears
- [ ] Manual: Submit form in modal, modal closes on success
- [ ] Manual: Click backdrop, modal closes
- [ ] Manual: Press Escape, modal closes
- [ ] Manual: Modal shows validation errors without closing

**Dependencies**: T061

---

## Phase 6D: Styling & Responsive Design (T066-T070)

### T066: Create Component CSS Library ⭕

**Objective**: Build reusable CSS components

**Tasks**:
- [ ] Create `frontend/static/css/components/buttons.css`
  - `.button` - Base button style
  - `.button-primary` - Primary action color
  - `.button-secondary` - Secondary action
  - `.button-danger` - Destructive action
  - `.button-small` - Smaller size variant
  - `.button-large` - Larger size variant
  - `.button-loading` - Disabled state with spinner
  - Hover/focus/active states
  - All using CSS variables for colors
- [ ] Create `frontend/static/css/components/cards.css`
  - `.card` - Base card
  - `.card-header` - Optional header section
  - `.card-body` - Main content
  - `.card-footer` - Optional footer/actions
  - Shadows, borders, spacing all from variables
- [ ] Create `frontend/static/css/components/forms.css`
  - `.form-group` - Label + input wrapper
  - `.form-input` - Text inputs, textareas
  - `.form-select` - Dropdowns
  - `.form-error` - Error state styling
  - `.form-help` - Helper text styling
  - `.form-label` - Label styling
  - Focus, disabled, error states
- [ ] Create `frontend/static/css/components/alerts.css`
  - `.alert` - Base alert
  - `.alert-success` - Success state
  - `.alert-danger` - Error state
  - `.alert-warning` - Warning state
  - `.alert-info` - Info state
  - Close button styling
- [ ] Create `frontend/static/css/components/tables.css`
  - `.table` - Base table styling
  - Row hover states
  - Alternating row colors
  - Responsive scrolling on mobile

**Deliverables**:
- ✅ `frontend/static/css/components/buttons.css` - 100 lines
- ✅ `frontend/static/css/components/cards.css` - 80 lines
- ✅ `frontend/static/css/components/forms.css` - 120 lines
- ✅ `frontend/static/css/components/alerts.css` - 60 lines
- ✅ `frontend/static/css/components/tables.css` - 70 lines

**Testing**:
- [ ] Manual: Check all button styles look correct in dark mode
- [ ] Manual: Check all button styles in light mode
- [ ] Manual: Hover/focus states work
- [ ] Manual: Form validation styling works
- [ ] Manual: Theme switching changes colors correctly

**Dependencies**: T052, T053

---

### T067: Create Layout & Base CSS ⭕

**Objective**: Build responsive grid and layout system

**Tasks**:
- [ ] Create `frontend/static/css/layout/base.css`
  - Root font sizing and line height
  - HTML, body, main styling
  - `.container` class (max-width, centered, padding)
  - Grid/flex utilities
  - Reset default margins/padding
- [ ] Create `frontend/static/css/layout/navbar.css`
  - Navigation bar sticky/fixed positioning
  - Navigation items layout
  - User menu dropdown styling
  - Theme switcher styling
  - Logo sizing
- [ ] Create `frontend/static/css/utilities/spacing.css`
  - Margin utilities: `.m-*`, `.mt-*`, `.mb-*`, `.ms-*`, `.me-*`
  - Padding utilities: `.p-*`, `.pt-*`, `.pb-*`, `.ps-*`, `.pe-*`
  - Sizes: xs (0.25rem), sm (0.5rem), md (1rem), lg (1.5rem), xl (2rem)
- [ ] Create `frontend/static/css/utilities/typography.css`
  - Heading styles: h1-h6
  - Typography classes: `.text-primary`, `.text-secondary`, `.text-muted`
  - Text sizing classes
  - Font weights
- [ ] Create `frontend/static/css/utilities/responsive.css`
  - Mobile first media queries
  - Breakpoints: 640px (tablet), 1024px (desktop)
  - Responsive utilities: `.hidden-mobile`, `.hidden-tablet`, etc.

**Deliverables**:
- ✅ `frontend/static/css/layout/base.css` - 100 lines
- ✅ `frontend/static/css/layout/navbar.css` - 80 lines
- ✅ `frontend/static/css/utilities/spacing.css` - 80 lines
- ✅ `frontend/static/css/utilities/typography.css` - 60 lines
- ✅ `frontend/static/css/utilities/responsive.css` - 50 lines

**Testing**:
- [ ] Manual: Pages layout correctly
- [ ] Manual: Navbar sticky/fixed works
- [ ] Manual: Container max-width proper
- [ ] Manual: Spacing utilities align elements
- [ ] Manual: Typography sizes look good

**Dependencies**: T066

---

### T068: Implement Responsive Design ⭕

**Objective**: Ensure mobile, tablet, desktop layouts work

**Tasks**:
- [ ] Test and fix all pages at three breakpoints:
  - Mobile: 375px (iPhone SE)
  - Tablet: 768px (iPad)
  - Desktop: 1440px (desktop)
- [ ] Adjust:
  - Navigation: Hamburger menu on mobile (HTMX expandable)
  - Grid layouts: Single column on mobile, multi-column on desktop
  - Form inputs: Full width on mobile
  - Card grid: 1 col mobile, 2 col tablet, 3+ col desktop
  - Tables: Horizontal scroll on mobile (or collapse to cards)
  - Font sizes: Smaller on mobile
  - Padding/margins: Smaller on mobile
- [ ] Create hamburger menu component for mobile nav
- [ ] Test touch interactions on mobile
- [ ] Test landscape orientation on mobile

**Deliverables**:
- ✅ All pages responsive
- ✅ `frontend/templates/components/mobile-nav.html` - Hamburger menu

**Testing**:
- [ ] Manual: DevTools responsive design mode
- [ ] Manual: Home page responsive
- [ ] Manual: Project list responsive
- [ ] Manual: Forms responsive
- [ ] Manual: Navigation mobile-friendly
- [ ] Manual: Touch interactions work

**Dependencies**: T067

---

### T069: Add Accessibility Features ⭕

**Objective**: Ensure WCAG AA compliance

**Tasks**:
- [ ] Semantic HTML:
  - Use `<button>` for buttons (not `<a>` styled as button)
  - Use `<nav>` for navigation
  - Use `<main>` for main content
  - Use `<form>` for forms
- [ ] ARIA labels:
  - Add `aria-label` to icon-only buttons
  - Add `aria-live="polite"` to dynamic content regions
  - Add `aria-hidden="true"` to decorative elements
- [ ] Color contrast:
  - Test with axe DevTools
  - Ensure WCAG AA standard (4.5:1 for text)
- [ ] Keyboard navigation:
  - Tab through all interactive elements
  - Focus indicators visible
  - No keyboard traps
- [ ] Form accessibility:
  - All inputs have associated labels
  - Error messages linked to inputs via `aria-describedby`
  - Required fields marked with `aria-required="true"`
- [ ] Image alt text:
  - All meaningful images have alt text
  - Decorative images have `alt=""`

**Deliverables**:
- ✅ All templates updated with semantic HTML and ARIA
- ✅ CSS for focus indicators

**Testing**:
- [ ] Manual: Keyboard navigation through pages
- [ ] Manual: Screen reader test (NVDA/JAWS if possible)
- [ ] Automated: axe DevTools audit (no violations)
- [ ] Automated: Lighthouse accessibility score > 90

**Dependencies**: T066-T068

---

### T070: Polish & Cross-Browser Testing ⭕

**Objective**: Final refinements and browser compatibility

**Tasks**:
- [ ] Test on browsers:
  - Chrome (latest)
  - Firefox (latest)
  - Safari (latest)
  - Edge (latest)
- [ ] Check:
  - Colors render correctly (theme switching)
  - CSS grid/flex layouts work
  - Forms submit correctly
  - HTMX interactions work
  - File uploads work
- [ ] Fix any rendering issues
- [ ] Optimize CSS file size
  - Remove unused styles
  - Combine media queries
  - Minify CSS (in production)
- [ ] Performance:
  - CSS file size < 50KB (uncompressed)
  - Load time < 1s (home page)
  - Theme switch < 100ms
- [ ] Visual polish:
  - Ensure consistent spacing
  - Check hover states
  - Verify button feedback
  - Review color contrast

**Deliverables**:
- ✅ All pages tested and working in all browsers
- ✅ CSS optimized
- ✅ `frontend/static/css/index.css` - Master CSS import file

**Testing**:
- [ ] Manual: Test each page in 4 browsers
- [ ] Manual: Test theme switching in each browser
- [ ] Manual: Test file uploads
- [ ] Performance: Lighthouse test

**Dependencies**: T066-T069

---

## Phase 6E: Testing & Deployment (T071-T075)

### T071: Unit Tests for Templates ⭕

**Objective**: Test template rendering and component logic

**Tasks**:
- [ ] Create `tests/unit/test_templates.py`
  - Test Jinja2 template rendering
  - Mock user context
  - Verify template variables are used
  - Test conditional blocks (authenticated vs anonymous)
  - Test loops (projects list, tags, etc.)
  - Test inheritance (base template works)
- [ ] Test each template:
  - base.html renders correctly
  - All pages extend base.html
  - Components render in isolation
  - Theme CSS loads
  - Forms render with correct inputs
- [ ] Coverage: > 80% of template code paths

**Deliverables**:
- ✅ `tests/unit/test_templates.py` - 200+ lines

**Testing**:
- [ ] Run `pytest tests/unit/test_templates.py -v`
- [ ] Verify coverage > 80%

**Dependencies**: T056-T060

---

### T072: Integration Tests for Pages ⭕

**Objective**: Test full page loads with backend integration

**Tasks**:
- [ ] Create `tests/integration/test_frontend_pages.py`
  - Test home page loads (unauthenticated)
  - Test login page loads
  - Test register page loads
  - Test projects page (requires auth)
  - Test project detail page
  - Test models upload page
  - Test API keys page
  - Test theme switching
  - Test theme persistence
  - Test HTMX interactions:
    - Create project via HTMX
    - Edit project via HTMX
    - Delete project with confirmation
    - Upload model file
    - Pagination
    - Search
- [ ] Mock database and API calls
- [ ] Use test client to make HTTP requests
- [ ] Verify response status codes
- [ ] Verify response HTML contains expected elements

**Deliverables**:
- ✅ `tests/integration/test_frontend_pages.py` - 300+ lines

**Testing**:
- [ ] Run `pytest tests/integration/test_frontend_pages.py -v`
- [ ] All tests pass
- [ ] Coverage of critical user flows

**Dependencies**: T071

---

### T073: End-to-End User Flow Tests ⭕

**Objective**: Test complete user journeys

**Tasks**:
- [ ] Create `tests/e2e/test_user_flows.py`
  - Test complete flow: Register → Create Project → Upload Model → Logout
  - Test: Login → Create Project → Edit Project → Delete Project
  - Test: Create API Key → Copy Secret → Revoke Key
  - Test: Change Theme → Verify Persistence → Switch Back
  - Test: Upload File → See in List → Delete → Confirm Gone
  - All using test client simulating real browser
- [ ] Each test is independent and can run in any order
- [ ] Use fixtures for setup/teardown
- [ ] Verify user sees expected pages at each step

**Deliverables**:
- ✅ `tests/e2e/test_user_flows.py` - 200+ lines

**Testing**:
- [ ] Run `pytest tests/e2e/test_user_flows.py -v`
- [ ] All user critical flows pass
- [ ] No test interdependencies

**Dependencies**: T072

---

### T074: Update Documentation ⭕

**Objective**: Document frontend setup and deployment

**Tasks**:
- [ ] Update `README.md`:
  - Add section: "Frontend Architecture"
  - Describe HTMX, Jinja2, CSS theming
  - Link to frontend development guide
- [ ] Create `docs/frontend-development.md`:
  - Setup instructions for frontend development
  - How to add new pages
  - How to add new components
  - How to add new themes (plugin system)
  - HTMX patterns and best practices
  - CSS variable system explanation
  - How to modify colors without touching code
- [ ] Create `docs/theming-guide.md`:
  - How to create new theme plugin
  - Color variable reference
  - Example: Create "high-contrast" theme
  - Example: Create "custom-company" theme
- [ ] Update `CHANGELOG.md`:
  - Add web frontend features
  - Update version to 1.1.0 (or 2.0.0 if major rewrite)
- [ ] Add deployment section to `docs/configuration.md`:
  - Docker setup for frontend + API
  - Nginx reverse proxy configuration
  - Environment variables for frontend
  - How to disable frontend if using separate deployment

**Deliverables**:
- ✅ `README.md` - Updated with frontend overview
- ✅ `docs/frontend-development.md` - 200+ lines
- ✅ `docs/theming-guide.md` - 150+ lines
- ✅ `docs/configuration.md` - Deployment section added

**Testing**:
- [ ] Manual: Read documentation, ensure it's clear
- [ ] Manual: Follow development guide to add new page (verify instructions work)
- [ ] Manual: Follow theming guide to create test theme

**Dependencies**: T073

---

### T075: Final Integration & Release ⭕

**Objective**: Full integration test and release

**Tasks**:
- [ ] Integration checklist:
  - [ ] All 52 existing API tests still pass
  - [ ] All 25 new frontend tests pass
  - [ ] No import errors
  - [ ] No circular import issues
  - [ ] FastAPI app starts without errors
  - [ ] All routes respond correctly
  - [ ] Theme system works
  - [ ] HTMX interactions work
  - [ ] Database migrations run
  - [ ] Devcontainer builds and starts
- [ ] Performance audit:
  - [ ] Home page load < 500ms
  - [ ] Theme switch < 100ms
  - [ ] API response < 200ms (with cache)
  - [ ] File upload progress shows
- [ ] Docker build:
  - [ ] Dockerfile builds successfully
  - [ ] docker-compose up works
  - [ ] All services start
  - [ ] Database initializes
  - [ ] App accessible at localhost:8000
- [ ] Update version:
  - [ ] `pyproject.toml` version to 2.0.0
  - [ ] `CHANGELOG.md` with release notes
  - [ ] Git tag: `v2.0.0-frontend`
- [ ] Final commits and push:
  - [ ] All files committed
  - [ ] Commit message: "Release v2.0.0: Add web UI (Phase 6)"
  - [ ] Push to remote
  - [ ] Create GitHub release

**Deliverables**:
- ✅ All tests passing
- ✅ Version updated to 2.0.0
- ✅ CHANGELOG updated
- ✅ Released on GitHub

**Testing**:
- [ ] Run full test suite: `pytest tests/ -v`
- [ ] Build Docker image
- [ ] Test docker-compose deployment
- [ ] Manual smoke test of all pages
- [ ] Verify theme switching works
- [ ] Verify HTMX interactions

**Dependencies**: T074

---

## Timeline

```
Week 1 (Feb 24-28)
- T051-T055: Theme system & base templates
- T056-T057: Home & auth pages

Week 2 (Mar 1-6)
- T058-T065: Project pages & HTMX
- T066-T070: Styling & responsive
- T071-T075: Testing & release
```

---

## Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| New Pages | 8+ | ✅ Complete |
| Components | 15+ | ✅ Complete |
| Tests | 25+ | 📋 Pending |
| Coverage | > 80% | 📋 Pending |
| Performance | < 500ms load | 📋 Pending |
| Accessibility | WCAG AA | 📋 Pending |
| Browser Support | 4 Major | 📋 Pending |
| Theme Plugin System | Working | ✅ Complete |

---

## Phase 6F: Admin Interface (T076-T080)

### T076: First-Time Setup Flow ⭕

**Objective**: Implement automatic admin account creation on startup

**Tasks**:
- [ ] Update User model (SQLAlchemy)
  - Add `is_admin: bool = False` column
  - Add `is_active: bool = True` column
  - Add database indexes
- [ ] Create Alembic migration for new columns
- [ ] Create SetupForm Pydantic model
  - Fields: username, email, password, confirm_password
  - Validation: password strength (8+ chars, mixed case, numbers)
- [ ] Add startup hook to check admin count
  - `app.state.setup_required = True` if no admins exist
- [ ] Create setup middleware
  - Redirects to /setup if setup_required and not on allowed routes
  - Allowed: /setup, /static/*, /api/v1/theme/css
- [ ] Implement GET /setup route
  - Render setup.html with form
  - Check if setup already done (redirect to /)
- [ ] Implement POST /setup route
  - Validate form data
  - Create admin user via UserService
  - Set app.state.setup_required = False
  - Set session and redirect to login
- [ ] Create frontend/templates/setup.html
  - Logo/branding section
  - Admin creation form
  - Theme preference selector (Dark/Light)
  - Submit button and success message

**Testing**:
- [ ] Test: First startup creates setup_required flag
- [ ] Test: Setup page renders when required
- [ ] Test: Admin account creation works
- [ ] Test: Setup complete redirects to login
- [ ] Test: Navigation redirects to setup when required
- [ ] Test: Setup hidden after completion

**Deliverables**:
- Alembic migration (add is_admin, is_active)
- SetupForm model
- Setup routes (GET, POST)
- Setup template
- Startup middleware
- Database migration applied

**Dependencies**: T051 (theme loaded in setup page)

**Timeline**: 1.5 days

---

### T077: Admin Dashboard & Navigation ⭕

**Objective**: Build admin overview dashboard with core statistics

**Tasks**:
- [ ] Create admin middleware/auth
  - Helper function: `get_admin_user()` dependency
  - Check user.is_admin flag
  - Return 403 if not admin
- [ ] Create GET /admin route
  - Calculate stats: user_count, project_count, model_count, storage_used
  - Get recent activity log (last 10 entries)
  - Render admin/dashboard.html
- [ ] Create frontend/templates/admin/base.html
  - Base template with admin nav
  - Sidebar with admin menu links
  - Top nav with user profile and logout
  - Theme switcher
  - Breadcrumb navigation
- [ ] Create sidebar navigation
  ```
  Admin Dashboard
  ├── Dashboard (overview)
  ├── Users (management)
  ├── Plugins (manager)
  ├── Settings (configuration)
  ├── Logs (viewer)
  └── Health (system status)
  ```
- [ ] Create frontend/templates/admin/dashboard.html
  - Stats cards (display counts and storage)
  - Recent activity list
  - System status indicator
  - Quick links section
  - Welcome message for new admin
- [ ] Style admin layout with responsive design
  - Mobile sidebar (hamburger toggle)
  - Tablet and desktop layouts
  - Dark/light theme support

**Testing**:
- [ ] Test: Admin route requires authentication
- [ ] Test: Admin route requires is_admin=True
- [ ] Test: Dashboard stats display correctly
- [ ] Test: Navigation renders all links
- [ ] Test: Breadcrumbs show correct path
- [ ] Test: Dashboard responsive on mobile

**Deliverables**:
- Admin authentication dependency
- GET /admin route
- admin/base.html template
- admin/dashboard.html template
- Admin navigation styling
- Test suite

**Dependencies**: T076 (admin user exists), T055 (theme system)

**Timeline**: 2 days

---

### T078: User Management Interface ⭕

**Objective**: Build CRUD interface for managing users

**Tasks**:
- [ ] Create admin routes for users
  - GET /admin/users - List users (paginated)
  - GET /admin/users/create - Create form modal
  - POST /admin/users/create - Create user
  - GET /admin/users/{id}/edit - Edit form modal
  - POST /admin/users/{id}/edit - Update user
  - DELETE /admin/users/{id} - Delete with confirmation
- [ ] Update UserService
  - Add count() method
  - Add list() method with pagination
  - Add filter methods (by username, email, role)
- [ ] Create frontend/templates/admin/users/list.html
  - Table with columns: username, email, role, created_at, last_login, actions
  - Pagination controls (next, prev, pages)
  - Search/filter box
  - Create new user button
- [ ] Create frontend/templates/admin/users/form.html (modal)
  - Username field (required, unique validation)
  - Email field (required, unique validation)
  - Password field (required for create, optional for edit)
  - Confirm password field
  - Role select (admin checkbox or dropdown)
  - Is active checkbox
  - Submit and cancel buttons
- [ ] Implement HTMX interactions
  - Show create form modal via HTMX (GET /admin/users/create)
  - Create user via HTMX form submission
  - Show edit form modal via HTMX
  - Update user via HTMX form submission
  - Delete with HTMX confirmation
  - Real-time table update after CRUD
- [ ] Add form validation
  - Username unique check
  - Email unique check
  - Password strength validation
  - Client-side + server-side validation

**Testing**:
- [ ] Test: List users page renders with pagination
- [ ] Test: Create form modal opens and validates
- [ ] Test: New user created successfully
- [ ] Test: Edit form loads current data
- [ ] Test: User updated successfully
- [ ] Test: Delete shows confirmation
- [ ] Test: User deleted successfully
- [ ] Test: Search/filter works

**Deliverables**:
- Admin user routes (GET, POST, DELETE)
- UserService extended with list/filter methods
- admin/users/list.html template
- admin/users/form.html template
- HTMX interactions
- Validation logic

**Dependencies**: T077 (admin navigation)

**Timeline**: 2 days

---

### T079: Plugin Manager & Settings ⭕

**Objective**: Build interface to manage plugins and system settings

**Tasks**:
- [ ] Create admin routes for plugins
  - GET /admin/plugins - List installed plugins
  - POST /admin/plugins/{id}/toggle-enable - Enable/disable plugin
  - GET /admin/plugins/{id}/config - Show config form modal
  - POST /admin/plugins/{id}/config - Save plugin configuration
- [ ] Extend PluginManager
  - Add get_all() method returning plugin metadata
  - Add get_by_id(id) method
  - Add toggle_enabled(id) method
  - Add get_config(id) and set_config(id, config) methods
- [ ] Create GET /admin/settings route
  - Render admin/settings.html
  - Load current settings (theme, log_level, etc.)
- [ ] Create frontend/templates/admin/plugins/list.html
  - Table with columns: name, type, version, status (enabled/disabled), actions
  - Enable/disable toggle per plugin
  - Configuration button per plugin
  - Plugin details (dependencies, description)
- [ ] Create frontend/templates/admin/plugins/config.html (modal)
  - Dynamic form based on plugin configuration schema
  - Save button
  - Show current config values
- [ ] Create frontend/templates/admin/settings.html
  - Theme selector (dropdown)
  - Log level selector (DEBUG, INFO, WARNING, ERROR)
  - Backup options (backup now button)
  - Restore from backup
  - Advanced settings (rate limiting, etc.)
- [ ] Implement HTMX interactions
  - Toggle plugin enable/disable button via HTMX
  - Open config modal for plugin
  - Save plugin config via HTMX
  - Update plugin list after changes
  - Save global settings via HTMX
- [ ] Add admin logging
  - Log all plugin enable/disable changes
  - Log all settings changes with who changed them

**Testing**:
- [ ] Test: List plugins page renders
- [ ] Test: Plugins enable/disable toggles work
- [ ] Test: Config modal opens with current settings
- [ ] Test: Save plugin config works
- [ ] Test: Settings page renders current values
- [ ] Test: Change theme setting persists
- [ ] Test: Log level change takes effect
- [ ] Test: Only admins can access these pages

**Deliverables**:
- Admin plugin routes
- PluginManager extended methods
- GET /admin/settings route
- admin/plugins/list.html template
- admin/plugins/config.html template
- admin/settings.html template
- HTMX interactions
- Admin audit logging

**Dependencies**: T077 (admin base), T031 (plugin system)

**Timeline**: 2 days

---

### T080: Logs Viewer & System Health ⭕

**Objective**: Build interface for system monitoring and troubleshooting

**Tasks**:
- [ ] Create admin routes for logs
  - GET /admin/logs - Fetch recent logs (JSON)
  - GET /admin/health - System health status (JSON)
- [ ] Extend logging system
  - Add method to fetch recent logs from file: logs_tail(n_lines, level=None)
  - Add method to filter logs: logs_filter(level, module, search_term)
  - Ensure JSON format for structured parsing
- [ ] Create frontend/templates/admin/logs.html
  - Log viewer with real-time tail display
  - Filter by level (DEBUG, INFO, WARNING, ERROR)
  - Filter by module/logger name
  - Search by message text
  - Download logs button
  - Auto-refresh toggle (refresh every 5 seconds)
  - Timestamp, level, module, message columns
- [ ] Create frontend/templates/admin/health.html
  - Storage usage card (progress bar)
  - Database connection status
  - API response time (average, 95th percentile)
  - User count, project count, model count
  - Uptime information
  - Last backup timestamp (if applicable)
  - System load/CPU info (if available)
- [ ] Implement HTMX interactions
  - Auto-refreshing logs display (HTMX polling every 2 seconds)
  - Filter logs via HTMX (no page reload)
  - Download logs file button
  - Real-time health updates (every 10 seconds)
- [ ] Add health check endpoints
  - GET /api/v1/health/storage - Storage status
  - GET /api/v1/health/database - Database status
  - GET /api/v1/health/api - API metrics
- [ ] Implement system monitoring
  - Calculate storage used (from storage service)
  - Database connection test
  - API response time tracking (middleware)
  - Uptime tracking

**Testing**:
- [ ] Test: Logs page renders with recent entries
- [ ] Test: Filter by level works
- [ ] Test: Search logs works
- [ ] Test: Auto-refresh updates logs
- [ ] Test: Download logs file works
- [ ] Test: Health page displays all metrics
- [ ] Test: Storage calculation correct
- [ ] Test: Database status accurate
- [ ] Test: Only admins can access

**Deliverables**:
- GET /admin/logs and /admin/health routes
- Logs filtering methods in logging
- Health check API routes
- admin/logs.html template
- admin/health.html template
- HTMX auto-refresh interactions
- System monitoring middleware/service
- Test suite

**Dependencies**: T077 (admin base), T039 (health checks)

**Timeline**: 2 days

---

## Dependencies & Blockers

**Dependencies**:
- Phase 1 MVP (API) complete ✅
- FastAPI running ✅
- Database working ✅
- Phases 6A-6E complete (before Phase 6F)

**No external blockers identified**

---

## Notes

- HTMX loaded from CDN (no build step needed)
- No new Python package dependencies
- Theme system extensible for future plugins
- Dark mode by default (user preference)
- All colors in CSS variables (no hardcoding)
- Mobile-first responsive design
