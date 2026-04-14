# Bug Tracking

Temporary tracker for pre-production bug history.

This file is organized by canonical bug ID in ascending order. It can be retired after the first production-stable release once issue/PR metadata is the long-term system of record.

## Conventions

- Canonical branch pattern for new bugs: `bugfix/<id>-<short-slug>`
- Branch values in this file are evidence-backed only
- If no branch evidence exists, field is left as `unknown`

## Open Issues

### Bug #24: API key scope validation missing
- Status: Open
- Severity: Low
- Component: Backend/API Keys
- Branch: unknown
- Created: 2026-02-22
- Description: API keys accept arbitrary scope values; API key auth flow is not fully implemented.
- Evidence: tests/validation/test_api_key_validation.py::TestAPIKeyUsageValidation::test_use_key_with_insufficient_scope

## Resolved and Historical (Sequential)

### Bug #1: Navbar does not update after login
- Status: Resolved
- Severity: High
- Component: Frontend/Auth
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: User context now passed from cookie-authenticated routes into templates.

### Bug #2: Admin link missing from navbar
- Status: Resolved
- Severity: Medium
- Component: Frontend/Templates
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Admin conditional now receives user context correctly.

### Bug #3: Projects page stuck on loading state
- Status: Resolved
- Severity: High
- Component: Frontend/Projects
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Added HTMX error/timeout handling and proper empty/error states.

### Bug #4: Theme toggle button not functioning
- Status: Resolved
- Severity: Low
- Component: Frontend/Theme
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Corrected click handling and dropdown interaction wiring.

### Bug #5: Admin logs frame/rendering issues
- Status: Resolved
- Severity: High
- Component: Frontend/Admin
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Corrected endpoint path and HTMX swap behavior for logs pane updates.

### Bug #6: Logout control alignment/styling regressions
- Status: Resolved
- Severity: Low
- Component: Frontend/UI
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Normalized logout action styling and interaction to match menu items.

### Bug #7: Theme toggle light/dark regression
- Status: Resolved
- Severity: Medium
- Component: Frontend/Theme
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Updated event handling and persistent theme-state behavior.

### Bug #8: Plugin loader logs abstract-class instantiation errors
- Status: Resolved
- Severity: Medium
- Component: Backend/Plugins
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Skip abstract classes and handle constructor-arg plugin classes gracefully.

### Bug #9: Logs filter did not actually filter data
- Status: Resolved
- Severity: High
- Component: Frontend/Backend/Admin
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Added trigger + request param wiring and backend filtering logic.

### Bug #10: Duplicate root-level backend/frontend directories
- Status: Resolved
- Severity: Medium
- Component: Project Structure
- Branch: bug/duplicate-root-directories
- Resolved In: 2026-02-22
- Resolution: Removed duplicate root-level directories and protected against recreation.

### Bug #11: Add project button non-functional
- Status: Resolved
- Severity: High
- Component: Frontend/Projects
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Added missing create-modal route and form-compatible backend handling.

### Bug #12: Add user button does not work (legacy report)
- Status: Resolved
- Severity: High
- Component: Frontend/Admin
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Superseded by implemented admin-user create flow (see Bug #26 note).

### Bug #13: Add plugin button non-functional
- Status: Resolved
- Severity: High
- Component: Frontend/Admin
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Corrected upload-modal URL path to API prefix.

### Bug #14: User profile page loads wrong/empty data
- Status: Resolved
- Severity: High
- Component: Frontend/Backend/Profile
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Added users/me endpoint and profile form endpoints.

### Bug #15: Admin user edit button non-functional
- Status: Resolved
- Severity: High
- Component: Frontend/Admin
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Fixed edit modal route, data load path, and update endpoint.

### Bug #16: XSS vulnerability in API key names
- Status: Resolved
- Severity: High
- Component: Backend/API Keys
- Branch: unknown
- Resolved In: Commit 19276a4
- Resolution: Added HTML/script sanitization and rejection for API key names.

### Bug #17: XSS vulnerability in user display names
- Status: Resolved
- Severity: High
- Component: Backend/Auth
- Branch: unknown
- Resolved In: Commit 19276a4
- Resolution: Applied input sanitization for display_name in registration flow.

### Bug #18: Duplicate username/email returned 422 instead of 409
- Status: Resolved
- Severity: Low
- Component: Backend/Auth
- Branch: unknown
- Resolved In: Commit b1e2824
- Resolution: Return 409 for duplicate identity conflicts.

### Bug #19: Very long passwords accepted without limit
- Status: Resolved
- Severity: Low
- Component: Backend/Auth Validation
- Branch: unknown
- Resolved In: Commit a639358
- Resolution: Added max-length validation for password input.

### Bug #20: Project title special-character validation gaps
- Status: Resolved
- Severity: Medium
- Component: Backend/Projects
- Branch: unknown
- Resolved In: Commit 90ab0e3
- Resolution: Added robust title length/whitespace/sanitization validation.

### Bug #21: Unicode project names rejected
- Status: Resolved
- Severity: Medium
- Component: Backend/Projects
- Branch: unknown
- Resolved In: Commit 90ab0e3
- Resolution: Validation now permits valid Unicode titles.

### Bug #22: API key revocation tests failing
- Status: Resolved
- Severity: Medium
- Component: Backend/API Keys
- Branch: unknown
- Resolved In: Commit 0da2006
- Resolution: Corrected test setup and response field assumptions.

### Bug #23: Project update endpoint returned 405
- Status: Resolved
- Severity: Medium
- Component: Backend/Projects
- Branch: unknown
- Resolved In: Commit dc643cd
- Resolution: Corrected method/handler flow and request parsing behavior.

### Bug #25: Projects table rows stacked vertically
- Status: Resolved
- Severity: High
- Component: Frontend/Projects
- Branch: bug/25-projects-table-row-layout
- Resolved In: Commit f789d49
- Resolution: Removed conflicting cell display override; added redraw safety and SRI.

### Bug #26: Admin user add workflow fix (renumbered legacy duplicate)
- Status: Resolved
- Severity: High
- Component: Frontend/Admin
- Branch: unknown
- Resolved In: 2026-02-22
- Resolution: Added admin user-create API and corrected modal path wiring.
- Note: Renumbered from legacy duplicate Bug #16 entry to maintain unique sequential IDs.

## Branch Evidence Ledger

Evidence-backed bug branches observed in local git history:

- bug/duplicate-root-directories -> mapped to Bug #10
- bug/25-projects-table-row-layout -> mapped to Bug #25

Observed bugfix branches not safely mappable to a specific bug record with current evidence:

- bugfix/setup-form-submission
- bugfix/admin-storage-logs-viewer-selection
