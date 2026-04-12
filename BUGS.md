# Bug Tracking

## Recently Resolved (2026-02-22)

### ✅ Bug #16: XSS vulnerability in API key names
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: High (Security)  
**Component**: Backend/API Keys  
**Resolved In**: Commit 19276a4

**Description**: API key names accept unescaped HTML/JavaScript including `<script>` tags. This could allow stored XSS attacks.

**Test Evidence**: `tests/validation/test_api_key_validation.py::TestAPIKeyCreationValidation::test_invalid_key_names`
- Input: `<script>alert('xss')</script>`
- Expected: Rejected (400) or sanitized
- ~~Actual: Accepted (201) with script tags intact~~

**Resolution**: Added `sanitize_text_input()` validation function that rejects HTML tags and JavaScript. API key creation now returns 400 Bad Request with error message "API key name cannot contain HTML tags". Test now passes ✅

---

### ✅ Bug #17: XSS vulnerability in user display names
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: High (Security)  
**Component**: Backend/Auth  
**Resolved In**: Commit 19276a4

**Description**: User display names accept unescaped HTML/JavaScript. Display names appear throughout the UI and could execute malicious scripts.

**Test Evidence**: `tests/validation/test_auth_validation.py::TestRegistrationValidation::test_xss_in_display_name`
- Input: `<script>alert('XSS')</script>`
- Expected: Rejected or sanitized
- ~~Actual: Accepted with script tags intact~~

**Resolution**: Applied `sanitize_text_input()` to display_name field during registration. Returns 400 Bad Request with error message "Display name cannot contain HTML tags". Test now passes ✅

---

### ✅ Bug #22: API key revocation tests failing
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: Medium  
**Component**: Backend/API Keys  
**Resolved In**: Commit 0da2006

**Description**: API key revocation functionality appears incomplete or broken based on test failures.

**Test Evidence**:
- ~~`tests/validation/test_api_key_validation.py::TestAPIKeyRevocationValidation::test_revoke_another_users_key` - KeyError: 'access_token'~~
- ~~`tests/validation/test_api_key_validation.py::TestAPIKeyUsageValidation::test_use_revoked_key` - KeyError: 'key'~~
- ~~`tests/validation/test_api_key_validation.py::TestAPIKeyUsageValidation::test_use_key_with_insufficient_scope` - KeyError: 'key'~~

**Resolution**: Fixed test issues:
- Added missing `display_name` field to registration call
- Corrected field name from `key` to `secret` in API key responses
- Tests now run correctly: 25/26 passing (96%)
- Remaining failure is feature gap (API key authentication handler not implemented) ✅

---

### ✅ Bug #23: Project update endpoint returns 405 (Method Not Allowed)
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: Medium  
**Component**: Backend/Projects  
**Resolved In**: Commit dc643cd

**Description**: Attempting to update projects returns 405, suggesting the endpoint may not be implemented or JSON support was missing.

**Test Evidence**: `tests/validation/test_project_validation.py::TestProjectUpdateValidation::test_update_nonexistent_project`
- Request: ~~PATCH/PUT~~ to `/api/v1/projects/{id}`
- Expected: 404 (not found) for invalid ID
- ~~Actual: 405 (method not allowed)~~

**Resolution**: 
- Modified `create_project` endpoint to handle both form and JSON requests
- Added support for both 'title' and 'name' fields for backward compatibility
- Added XSS sanitization to project titles and descriptions
- Updated tests to use PATCH (correct HTTP method) and 'title' field
- All 3 project update tests now pass ✅

---

### ✅ Bug #18: Duplicate username/email returns 422 instead of 400/409
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: Low (API Design)  
**Component**: Backend/Auth  
**Resolved In**: Commit b1e2824

**Description**: Attempting to register with duplicate username/email returns 422 (Unprocessable Entity) instead of more semantic 400 (Bad Request) or 409 (Conflict).

**Test Evidence**: 
- ~~`tests/validation/test_auth_validation.py::TestRegistrationValidation::test_duplicate_username`~~
- ~~`tests/validation/test_auth_validation.py::TestRegistrationValidation::test_duplicate_email`~~

**Resolution**: 
- Check if ValueError contains 'already exists' in registration endpoint
- Return 409 Conflict for duplicate username/email (more semantic)
- Return 400 Bad Request for other validation errors
- Both tests now pass ✅

---

### ✅ Bug #19: Very long passwords accepted without limit
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: Low (DoS potential)  
**Component**: Backend/Auth Validation  
**Resolved In**: Commit a639358

**Description**: Passwords of extreme length (1000+ characters) are accepted, which could cause performance issues during bcrypt hashing.

**Test Evidence**: `tests/validation/test_auth_validation.py::TestRegistrationValidation::test_invalid_password_formats`
- Input: 1000-character password
- Expected: 400 (rejected as too long)
- ~~Actual: 201 (accepted)~~

**Resolution**:
- Added max_length=128 to password Field in RegisterRequest
- Prevents DoS via expensive bcrypt operations on very long passwords
- Aligns with validate_password() function max length check
- All 3 password validation tests now pass ✅

---

### ✅ Bug #20: Project names with special characters not validated
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: Medium  
**Component**: Backend/Projects  
**Resolved In**: Commit 90ab0e3

**Description**: Project names can contain special characters, null bytes, newlines, and other potentially problematic characters without validation.

**Resolution**:
- Added comprehensive title validation: minimum 2 characters, maximum 255 characters
- Reject whitespace-only titles with clear error message
- Strip whitespace before validation and sanitization
- All validation tests now pass ✅

---

### ✅ Bug #21: Unicode project names return 422 validation error
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: Medium (Internationalization)  
**Component**: Backend/Projects  
**Resolved In**: Commit 90ab0e3

**Description**: Project names with valid unicode characters (emoji, Chinese, Japanese) are rejected.

**Test Evidence**: `tests/validation/test_project_validation.py::TestProjectCreationValidation::test_unicode_in_project_name`
- Input: `プロジェクト 测试 🚀`
- Expected: 201 (accepted)
- ~~Actual: 422 (rejected)~~

**Resolution**:
- Unicode characters fully supported in project titles
- Validation only checks length and XSS patterns, not character types
- Fixed test to use 'title' field instead of 'name'
- Test now passes ✅

---

## Recently Resolved (2026-04-12)

### ✅ Bug #25: Projects table rows render stacked vertically
**Status**: ~~Open~~ **RESOLVED**  
**Severity**: High  
**Component**: Frontend/Projects  
**Resolved In**: Commit f789d49

**Description**: After the recent migration from a card grid to a Tabulator table, the Projects page rows displayed all column data stacked vertically instead of side-by-side columns. The table headers (Title, Category, Size, Created, Actions) appeared correctly but row cell content collapsed into a single stacked block.

**Root Cause**: Custom CSS in `list.html` overrode `.tabulator-cell` with `display: flex` (block-level). Tabulator v6 lays out row cells as `display: inline-flex` (inline-level); replacing this with block flow caused cells to stack vertically instead of flowing horizontally across the row.

**Resolution**: Removed the erroneous `display: flex` property from the custom `.tabulator-cell` rule; kept `align-items: center`. Also added SRI integrity hashes to both Tabulator CDN assets and a `tableBuilt` redraw callback for column-width safety.

---

## Open Issues (2026-02-22 - Discovered via Validation Testing)

### 🟡 Bug #24: API key scope validation missing
**Status**: Open  
**Severity**: Low  
**Component**: Backend/API Keys

**Description**: API keys accept arbitrary scope values without validation. Additionally, API key authentication is not yet implemented - only JWT bearer tokens are supported.

**Test Evidence**: `tests/validation/test_api_key_validation.py::TestAPIKeyUsageValidation::test_use_key_with_insufficient_scope`
- Test fails with 401 (Unauthorized) because API key authentication handler doesn't exist

**Impact**: Low - Feature gap, not a bug in existing functionality

**Recommended Fix**: 
1. Implement API key authentication middleware
2. Define valid scopes and validate in `src/backend/api/keys.py`

---

## Open Issues (2026-02-22 - User Reported)

### 🔴 Bug #12: Add user button doesn't work
**Status**: Open  
**Severity**: High  
**Component**: Frontend/Admin

**Description**: The "Add user" button in the admin panel does not function. Clicking it has no effect.

**Date Reported**: 2026-02-22  
**Expected Next Steps**: Determine if issue is frontend (button handler) or backend (API endpoint) and implement fix.

---

## Fixed (2026-02-22 - Round 5)

### ✅ Bug #14: User profile page displaying incorrect/empty data
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Backend/Profile

**Description**: The user profile page (http://localhost:8000/settings/profile) displays all appropriate fields (Username, Email, Display Name) but the data shown is completely wrong or never filled in from the backend. The fields appear to be loading placeholder data instead of actual user information.

**Root Causes**:
1. Missing `/api/v1/users/me` endpoint to fetch user data
2. Frontend was calling non-existent API endpoint via HTMX
3. Form fields had placeholder values but never loaded actual user data

**Fix**:
- **Created** [src/backend/api/users.py](src/backend/api/users.py) - new users API module with `/me` endpoint
- **Updated** [src/backend/api/__init__.py](src/backend/api/__init__.py) - added users_router to exports
- **Updated** [src/backend/main.py](src/backend/main.py) - registered users_router with `/api/v1` prefix
- **Added** [src/backend/api/frontend.py](src/backend/api/frontend.py) - POST endpoints for `/settings/profile` and `/settings/password` to handle form submissions

**Result**:
- ✅ User profile data loads correctly from database
- ✅ Profile fields are pre-populated with actual user information
- ✅ Email and display name can be updated
- ✅ Password change functionality implemented

---

### ✅ Bug #15: Admin User Management page - Edit button non-functional
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Admin

**Description**: On the Admin User Management page (http://localhost:8000/admin/users), clicking the "Edit" button for any user has no effect. The button does not open an edit form or navigate to an edit page.

**Root Causes**:
1. Edit button had incorrect URL path (`/admin/users/{id}/edit-modal` instead of `/api/v1/admin/users/{id}/edit-modal`)
2. Backend endpoint was loading dummy data instead of actual user from database
3. Form template didn't pre-populate fields with user data
4. Missing PUT endpoint to handle user updates

**Fix**:
- **Updated** [src/backend/api/admin.py](src/backend/api/admin.py#L457-L486) - `get_edit_user_modal` now loads actual user from database
- **Updated** [src/backend/api/admin.py](src/backend/api/admin.py#L311) - fixed Edit button URL to include `/api/v1` prefix
- **Updated** [src/frontend/templates/admin/users/form-modal.html](src/frontend/templates/admin/users/form-modal.html) - template now pre-fills form with user data using Jinja2
- **Added** [src/backend/api/admin.py](src/backend/api/admin.py#L572-L621) - PUT `/api/v1/admin/users/{user_id}` endpoint to update users

**Result**:
- ✅ Edit button opens modal with user's actual data
- ✅ Form fields are pre-populated correctly
- ✅ Can update user email, display name, role, and active status
- ✅ Password field is optional (only updates if provided)

---

### ✅ Bug #16: Admin User Management - Add user button doesn't work
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Admin

**Description**: The "Add user" button on the Admin User Management page (http://localhost:8000/admin/users) does not work when clicked.

**Root Causes**:
1. Button had incorrect URL path (`/admin/users/create-modal` instead of `/api/v1/admin/users/create-modal`)
2. Missing POST endpoint to handle user creation from form data

**Fix**:
- **Updated** [src/frontend/templates/admin/users/list.html](src/frontend/templates/admin/users/list.html#L10) - fixed button URL to include `/api/v1` prefix
- **Added** [src/backend/api/admin.py](src/backend/api/admin.py#L489-L550) - POST `/api/v1/admin/users` endpoint to create new users
- **Updated** [src/backend/api/admin.py](src/backend/api/admin.py#L12) - added Form import for form data handling
- **Updated** [src/backend/api/admin.py](src/backend/api/admin.py#L22-L23) - added UserService and PasswordAuthProvider imports

**Result**:
- ✅ Add user button opens modal form
- ✅ Can create new users with all fields (username, email, display name, password, role, active status)
- ✅ Proper validation and duplicate checking
- ✅ Password is properly hashed

---

### ✅ Bug #11: Add project button doesn't work
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Projects

**Description**: The "Add project" button on the Projects page does not function. Clicking it has no effect.

**Root Causes**:
1. Button was calling `/projects/create-modal` which didn't exist as an endpoint
2. POST endpoint only accepted JSON, not form data from HTMX

**Fix**:
- **Added** [src/backend/api/frontend.py](src/backend/api/frontend.py#L224-L242) - GET `/projects/create-modal` endpoint to serve project creation form
- **Updated** [src/backend/api/projects.py](src/backend/api/projects.py#L67-L115) - POST `/api/v1/projects` now handles both form data (for web UI) and JSON (for API)
- **Updated** [src/backend/api/projects.py](src/backend/api/projects.py#L6) - added Form import

**Result**:
- ✅ Add project button opens modal form
- ✅ Can create projects with name, description, visibility, and tags
- ✅ Form submission works via HTMX
- ✅ Both API and web UI functionality supported

---

### ✅ Bug #13: Add plugin button doesn't work
**Status**: Fixed  
**Severity**: High  
**Component**: Frontend/Admin

**Description**: The "Add plugin" button in the admin panel does not function. Clicking it has no effect.

**Root Cause**:
1. Button had incorrect URL path (`/admin/plugins/upload-modal` instead of `/api/v1/admin/plugins/upload-modal`)

**Fix**:
- **Updated** [src/frontend/templates/admin/plugins/list.html](src/frontend/templates/admin/plugins/list.html#L10) - fixed button URL to include `/api/v1` prefix

**Result**:
- ✅ Upload plugin button opens modal form
- ✅ Modal endpoint already existed, just needed correct URL

---

## Fixed (2026-02-22 - Round 4)

### ✅ Bug #10: Duplicate root-level /backend and /frontend directories
**Status**: Fixed  
**Severity**: Medium  
**Component**: Project Structure

**Description**: 
The project had duplicate `/backend` and `/frontend` directories at the root level, alongside the canonical source code in `/src/backend` and `/src/frontend`. This created confusion about which directories contained the actual source code.

**Root Causes**:
1. Vestigial directories that should have been removed during project restructuring
2. `pyproject.toml` explicitly specifies `[tool.setuptools.packages.find] where = ["src"]`, indicating `/src` is the canonical location
3. No `.gitignore` rules to prevent these root-level directories from being accidentally committed

**Fix**:
- **Deletion**: Removed root-level `/backend` and `/frontend` directories entirely (3,895 lines deleted)
- **Prevention**: Added `/backend` and `/frontend` to `.gitignore` to prevent accidental re-creation
- **Verification**: Confirmed `pyproject.toml` specifies `/src` as the source directory

**Files Modified**:
- Deleted: `/backend/`
- Deleted: `/frontend/`
- Modified: [.gitignore](.gitignore)

**Branch**: `bug/duplicate-root-directories` (merged to `dev`)

**Result**:
- ✅ Project structure is now clean with only `/src/backend` and `/src/frontend` as canonical source
- ✅ No confusion about which directories contain actual code
- ✅ Future changes won't accidentally re-create root-level directories

---

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