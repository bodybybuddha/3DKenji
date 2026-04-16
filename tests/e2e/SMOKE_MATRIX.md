# Frontend Smoke Automation Matrix

This matrix maps the manual release checklist to automated smoke coverage.

## Coverage Legend

- `PW`: Playwright test (pytest)
- `CDP`: Chrome DevTools MCP checks (console/network/lighthouse/perf)
- `PASS`: Implemented and expected to run now
- `PENDING`: Scaffolded, requires known app fixes/config

## Public and Shell Pages

| ID | Area | Route/Flow | Automation | Test | Status |
|---|---|---|---|---|---|
| SMK-PUB-001 | Landing page | `/` renders core CTA links | PW | `tests/e2e/test_smoke_public_pages.py::test_landing_page_loads_and_shows_primary_cta` | PASS |
| SMK-PUB-002 | Login page | `/login` form visible | PW | `tests/e2e/test_smoke_public_pages.py::test_login_page_loads` | PASS |
| SMK-PUB-003 | Register page | `/register` form visible | PW | `tests/e2e/test_smoke_public_pages.py::test_register_page_loads` | PASS |
| SMK-PUB-004 | Setup routing | `/setup` is form or redirect to login | PW | `tests/e2e/test_smoke_public_pages.py::test_setup_page_behavior` | PASS |

## Authenticated User Pages and Dialogs

| ID | Area | Route/Flow | Automation | Test | Status |
|---|---|---|---|---|---|
| SMK-USER-001 | Projects page | `/projects` and New Project button | PW | `tests/e2e/test_smoke_user_pages.py::test_projects_page_loads_for_authenticated_user` | PASS |
| SMK-USER-002 | Project create modal | Open/close create modal | PW | `tests/e2e/test_smoke_user_pages.py::test_project_create_modal_opens_and_closes` | PASS |
| SMK-USER-003 | API keys page | `/keys` and Generate Key button | PW | `tests/e2e/test_smoke_user_pages.py::test_api_keys_page_loads_for_authenticated_user` | PASS |
| SMK-USER-004 | API key modal | Open/close generate key modal | PW | `tests/e2e/test_smoke_user_pages.py::test_api_key_modal_opens_and_closes` | PASS |
| SMK-USER-005 | Profile settings | `/settings/profile` forms visible | PW | `tests/e2e/test_smoke_user_pages.py::test_profile_settings_page_loads` | PASS |
| SMK-USER-006 | Project upload dialog | Upload modal open from detail page | PW | `tests/e2e/test_smoke_user_pages.py::test_project_upload_modal_route_exists` | PASS |

## Admin Pages

| ID | Area | Route/Flow | Automation | Test | Status |
|---|---|---|---|---|---|
| SMK-ADM-001 | Admin access control | Non-admin redirected from `/admin*` | PW | `tests/e2e/test_smoke_admin_pages.py::test_non_admin_is_redirected_from_admin_routes` | PASS |
| SMK-ADM-002 | Admin dashboard | `/admin` loads for admin | PW | `tests/e2e/test_smoke_admin_pages.py::test_admin_dashboard_loads` | PENDING (env creds) |
| SMK-ADM-003 | Admin subpages | users/plugins/settings/logs/health load | PW | `tests/e2e/test_smoke_admin_pages.py::test_admin_subpages_load` | PENDING (env creds) |

## Browser Observability and Quality Signals (CDP)

| ID | Area | Target | Automation | Check | Status |
|---|---|---|---|---|---|
| CDP-001 | Console hygiene | Core routes | CDP | No uncaught errors on load/navigation | PENDING |
| CDP-002 | Network hygiene | Core routes | CDP | No failed critical requests (4xx/5xx exceptions reviewed) | PENDING |
| CDP-003 | Accessibility baseline | Landing, login, projects | CDP | Lighthouse accessibility score threshold | PENDING |
| CDP-004 | Best-practice baseline | Landing, projects, admin dashboard | CDP | Lighthouse best practices score threshold | PENDING |
| CDP-005 | Perf baseline | Landing and projects | CDP | Trace capture and budget checks | PENDING |

## Recently Resolved Blockers

- Added project upload modal route: `/projects/{project_id}/upload-modal`.
- Added profile account deletion endpoint: `DELETE /settings/account`.
- Added admin plugin upload endpoint: `POST /api/v1/admin/plugins/upload`.
