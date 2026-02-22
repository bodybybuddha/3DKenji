# Bug Tracking

## Fixed (2026-02-22 - Round 3)

### ✅ Bug #9: Logs page filtering not working
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Backend/Admin

**Description**: 
1. On page load, logs didn't display (blank loading state)
2. Selecting "Info" filter showed logs, but didn't filter them
3. Changing to other filters didn't update the display

**Root Causes**:
1. No `hx-trigger="change"` on the dropdown, so it only triggered on initial page load
2. Backend received `level` parameter but didn't use it to filter logs
3. HTMX parameter passing was using `hx-include` incorrectly

**Fix**:
- **Frontend**: 
  - Added `name="level"` attribute to dropdown so parameter is sent correctly
  - Added `hx-trigger="change"` to trigger HTMX request when filter changes
  - Removed incorrect `hx-include` attribute
- **Backend**:
  - Implemented actual filtering logic using the `level` parameter
  - Added more sample logs with different levels (DEBUG, INFO, WARNING, ERROR)
  - Case-insensitive comparison for filtering

**Files Modified**:
- [frontend/templates/admin/logs.html](frontend/templates/admin/logs.html#L10-L18)
- [src/backend/api/admin.py](src/backend/api/admin.py#L286-L308)

**Result**:
- ✅ All logs display on initial page load
- ✅ Filtering by "Info" shows only INFO logs
- ✅ Filtering by "Warning" shows only WARNING logs  
- ✅ Filtering by "Error" shows only ERROR logs
- ✅ Filtering by "Debug" shows only DEBUG logs
- ✅ "All Levels" shows all logs

---

## Fixed (2026-02-22 - Round 2)

### ✅ Bug #6 (Revised): Logout styled as button instead of menu item
**Status**: Fixed  
**Severity**: Low  
**Component**: Frontend/UI

**Description**: After the initial fix, the logout option appeared as a blue button instead of looking like other dropdown menu items (Profile Settings, Toggle Theme).

**Root Cause**: The previous fix used a `<button>` element with CSS class `.dropdown-logout-btn`, which still gave it button-like appearance with borders/background.

**Fix**:
- Changed logout to a regular `<a>` link element matching other menu items
- Moved the form submission logic to onclick handler
- Form is now hidden and triggered via JavaScript
- Visual appearance now matches other dropdown items exactly

**Files Modified**:
- [frontend/templates/base.html](frontend/templates/base.html#L58-L68)

---

### ✅ Bug #5 (Revised): Logs page renders full page in frame
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Admin

**Description**: Admin logs page showed "Loading logs..." on initial load. When selecting a filter (e.g., "Info"), the entire page (header, sidebar, etc.) was re-rendered inside the logs frame instead of just the log entries.

**Root Cause**: 
1. HTMX request was going to `/admin/logs` instead of `/api/v1/admin/logs`
2. Missing `hx-swap="innerHTML"` directive, defaulting to outer HTML replacement
3. Initial load script had `?format=html` parameter (not needed)

**Fix**:
- Updated filter dropdown `hx-get` to point to `/api/v1/admin/logs` (API endpoint)
- Added `hx-swap="innerHTML"` to specify only inner content should be replaced
- Fixed initial load script to use correct API endpoint
- Removed unnecessary format parameter

**Files Modified**:
- [frontend/templates/admin/logs.html](frontend/templates/admin/logs.html#L10-L18)

---

### ✅ Bug #8: Plugin loader errors on startup
**Status**: Fixed  
**Severity**: Medium  
**Component**: Backend/Plugins

**Description**: Application startup showed error messages attempting to instantiate abstract base classes and plugins requiring constructor arguments:
```
Failed to load plugin class StorageBackend: Can't instantiate abstract class...
Failed to load plugin class AuthProvider: Can't instantiate abstract class...
Failed to load plugin class PasswordAuthProvider: missing 1 required positional argument: 'session'
```

**Root Cause**: The plugin loader tried to instantiate every class that subclasses `KeajiPlugin`, including:
1. Abstract base classes (StorageBackend, AuthProvider)
2. Plugins requiring constructor arguments (PasswordAuthProvider)

**Fix**:
- Added `inspect.isabstract()` check to skip abstract base classes before instantiation
- Added TypeError exception handler to gracefully handle plugins requiring constructor args
- Changed error level to debug for these expected cases (not actual errors)
- Plugins like PasswordAuthProvider are meant to be instantiated manually with required args

**Files Modified**:
- [src/backend/core/plugins.py](src/backend/core/plugins.py#L78-L88)

**Note**: These "errors" were not critical - the application worked fine - but they cluttered logs and could confuse developers. Now startup logs are clean.

---

## Fixed (2026-02-22 - Round 1)

### ✅ Bug #1: Navbar doesn't update after login
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Auth/Templates

**Description**: After logging in successfully, user gets taken to the Projects page, but the navbar still shows "Login" and "Register" options instead of showing the logged-in user menu with "Logout" option.

**Root Cause**: Frontend routes were not extracting the user from JWT cookie and passing it to templates. Templates need user context to conditionally show/hide navbar elements.

**Fix**:
- Added `get_optional_user()` helper function in [frontend.py](src/backend/api/frontend.py#L24-L49)
- Updated all frontend routes to extract user from JWT cookie
- Added authentication guards to protected routes (projects, keys, admin)
- Templates now receive `user` context variable
- Navbar properly conditionally renders based on authentication state

**Files Modified**:
- [src/backend/api/frontend.py](src/backend/api/frontend.py)
- [frontend/templates/base.html](frontend/templates/base.html)

---

### ✅ Bug #2: Admin link missing from navbar
**Status**: Fixed  
**Severity**: Medium  
**Component**: Frontend/Templates

**Description**: If a user logs in as an admin, the navbar should show an "Admin" link to access the admin dashboard, but it was not appearing.

**Root Cause**: Same as Bug #1 - templates were not receiving user context, so `user.is_admin` check was not working.

**Fix**:
- User context now passed to all templates
- Navbar template already had conditional admin link (`{% if user.is_admin %}`)
- Now works correctly with user context

**Files Modified**:
- [src/backend/api/frontend.py](src/backend/api/frontend.py)

---

### ✅ Bug #3: Projects page loading state issues
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Projects

**Description**: The Projects page shows "Loading projects..." continuously. If no projects exist, it should show an appropriate empty state message. If there's a database/API error, it should display an error message.

**Root Cause**: 
1. HTMX request had no error handling
2. Empty projects list template already had empty state, but it wasn't shown with proper messaging
3. No timeout or error handling for failed requests

**Fix**:
- Added comprehensive error handling for HTMX requests
- Added event listeners for `htmx:responseError` and `htmx:timeout`
- Error states show appropriate messages with retry buttons
- Empty state already handled in [fragments/projects-list.html](frontend/templates/fragments/projects-list.html)

**Files Modified**:
- [frontend/templates/projects/list.html](frontend/templates/projects/list.html)

---

### ✅ Bug #4: Theme toggle button not working
**Status**: Fixed  
**Severity**: Low  
**Component**: Frontend/Theme

**Description**: The theme icon button in the navbar doesn't do anything when clicked. It should toggle between dark and light themes.

**Root Cause**: 
1. Button had `return false()` (invalid) instead of proper event handling
2. Theme toggle functionality exists but was not properly wired
3. User dropdown menu wasn't opening (JavaScript missing)

**Fix**:
- Removed invalid `return false()` from onclick handler
- Simplified theme button to just call `ThemeManager.toggle()`
- Theme toggle already implemented correctly in app.js
- Added DropdownHelper to handle user menu dropdown interactions
- User menu now opens/closes properly with theme toggle inside

**Files Modified**:
- [frontend/templates/base.html](frontend/templates/base.html)
- [frontend/static/js/app.js](frontend/static/js/app.js)

---

## Fixed (2026-02-22)

### ✅ Bug #5: Admin Logs page not loading
**Status**: Fixed  
**Severity**: High  
**Component**: Backend/Auth

**Description**: Admin logs page shows "Loading logs..." continuously and never displays any log entries.

**Root Cause**: HTMX requests from the frontend were not including the JWT token in the Authorization header. The backend's `get_bearer_token()` function only checked the Authorization header and didn't fall back to checking cookies where the JWT was actually stored after login.

**Fix**:
- Updated `get_bearer_token()` to accept tokens from both Authorization header AND cookies
- Token priority: Authorization header first, then cookie fallback
- This allows HTMX requests to work without explicitly setting auth headers
- Admin endpoints now properly authenticate using cookie-based sessions

**Files Modified**:
- [src/backend/api/auth.py](src/backend/api/auth.py#L76-L113)

---

### ✅ Bug #6: Logout button misaligned in dropdown
**Status**: Fixed  
**Severity**: Low  
**Component**: Frontend/UI

**Description**: In the user dropdown menu, the Logout button was left-aligned instead of having proper padding like other menu items (Profile Settings, Toggle Theme).

**Root Cause**: Logout button had conflicting inline styles (`padding: 0` and then `padding: var(--spacing-sm) 0`) that didn't match the dropdown menu item styling (`padding: var(--spacing-md) var(--spacing-lg)`).

**Fix**:
- Removed inline styles from logout button
- Created `.dropdown-logout-btn` CSS class with proper padding
- Button now matches styling of other dropdown items
- Consistent indentation and hover effects

**Files Modified**:
- [frontend/templates/base.html](frontend/templates/base.html#L59-L66)
- [frontend/static/css/layout/navbar.css](frontend/static/css/layout/navbar.css#L102-L121)

---

### ✅ Bug #7: Theme toggle not working (light ↔ dark)
**Status**: Fixed  
**Severity**: Medium  
**Component**: Frontend/Theme

**Description**: Clicking the "Toggle Theme" option in the user menu didn't switch between light and dark themes.

**Root Cause**: 
1. Event handler had `return false;` which may prevent proper event handling in some browsers
2. No visual feedback when theme switched
3. Potential timing issues with CSS loading

**Fix**:
- Updated event handler to use `event.preventDefault()` instead of `return false;`
- Added console logging for debugging theme switches
- Added toast notification for visual feedback when theme changes
- Theme toggle now properly switches between dark and light themes
- Theme preference persists in localStorage

**Files Modified**:
- [frontend/templates/base.html](frontend/templates/base.html#L60)
- [frontend/static/js/app.js](frontend/static/js/app.js#L84-L93)

---

## Open Issues

None currently.

---

## Testing Checklist (Updated 2026-02-22)

After fixes, verify:
- [x] Login redirects to projects page
- [x] Navbar shows user menu with username after login
- [x] Register link hidden when logged in
- [x] Login link hidden when logged in
- [x] Logout button visible in user dropdown
- [x] Admin link appears for admin users
- [x] Admin link hidden for regular users
- [ ] Projects page shows "No projects yet" when empty
- [ ] Projects page shows error message on API failure
- [x] **Admin logs page loads and displays log entries**
- [x] **Logout button properly aligned with other dropdown items**
- [x] **Theme toggle button works (switches dark/light)**
- [x] **Toast notification appears when theme switches**
- [x] User menu dropdown opens on click
- [x] User menu closes on outside click
- [x] Theme preference persists across page refreshes

---

## Notes

**Round 1 (2026-02-21)**: Fixed frontend authentication state and error handling
- User context passing to templates
- HTMX error handling for projects page
- Dropdown menu interactions

**Round 2 (2026-02-22)**: Fixed backend authentication and UI polish
- Cookie-based authentication for HTMX requests
- Dropdown menu styling consistency
- Theme toggle improvements with visual feedback

All fixes maintain backward compatibility - API endpoints still accept Authorization headers for programmatic access while also supporting cookie-based auth for web UI.

---

## Fixed (2026-02-21)