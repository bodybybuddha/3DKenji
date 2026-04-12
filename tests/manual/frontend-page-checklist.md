# Frontend Release Checklist (Page-by-Page)

Use this checklist before adding new features or cutting a release.

Legend:
- [ ] Not started
- [~] In progress
- [x] Verified
- [!] Defect found

## 1. Global Shell / Shared UX

Scope: base layout, nav, footer, theme toggle, toasts, dropdowns, HTMX/global JS.

- [ ] Verify top nav links route correctly for guest and authenticated users.
- [ ] Verify user dropdown opens/closes by click and outside click.
- [ ] Verify logout form submits and redirects as expected.
- [ ] Verify theme toggle persists across page reloads.
- [ ] Verify toast close and auto-dismiss behavior.
- [ ] Verify footer links resolve to the intended destination.

Update items found in code:
- [ ] Confirm footer link `/docs` is intentional (currently points to API Swagger path in FastAPI defaults, not MkDocs site content).

## 2. Landing Page (`/`)

- [ ] Guest CTAs route to login/register.
- [ ] Authenticated CTAs route to projects/keys/admin.
- [ ] All feature cards render without layout overflow on mobile.
- [ ] Verify role-based visibility for Admin CTA.

## 3. First-Time Setup (`/setup`)

- [ ] Validate required fields and client-side password confirmation.
- [ ] Validate server-side errors render in alert fragment.
- [ ] Verify successful setup redirects to login.
- [ ] Verify setup guard redirects non-setup routes when setup is required.

## 4. Auth Pages

### Login (`/login`)
- [ ] Invalid credentials show user-safe error.
- [ ] Valid login redirects to projects.
- [ ] Remember-me checkbox behavior is consistent with backend session behavior.
- [ ] Forgot-password link behavior is defined (currently placeholder `#`).

### Register (`/register`)
- [ ] Password mismatch blocked client-side.
- [ ] Duplicate username/email error shown clearly.
- [ ] Successful register logs in and redirects.
- [ ] Terms checkbox required flow verified.

Update items found in code:
- [ ] Ensure E2E tests use `/register` for registration, not `/setup`.

## 5. Projects List (`/projects`)

- [ ] Projects list loads into the table view and shows the total project count.
- [ ] Empty state appears inside the table when no projects exist.
- [ ] Retry/error UI appears when the projects table fetch fails.
- [ ] Sorting works for the visible columns.
- [ ] New Project modal opens/closes and submits correctly.

### Project Create/Edit Modal
- [ ] Create submits and refreshes the projects table.
- [ ] Edit pre-fills fields and saves updates.
- [ ] Validation errors render in modal alert container.
- [ ] Cancel/close controls remove modal.

## 6. Project Detail (`/project/{project_id}`)

- [ ] Edit and Delete actions work.
- [ ] Delete confirm prompt appears and redirects to projects on success.
- [ ] Models list loads and updates model count/size indicators.
- [ ] Storage info reflects real project directory status.

### Project Files Upload
- [ ] Upload File control is visible from the Project Files toolbar.
- [ ] Hidden file input and uploader drop zone are present.
- [ ] Upload progress/feedback updates during file upload.
- [ ] Success refreshes the Project Files table and summary.

Update items found in code:
- [x] Added route for `/projects/{project_id}/upload-modal`.
- [x] Added hidden `project_id` field in upload modal form.
- [x] Aligned accepted file types between UI and backend (`.stl,.3mf,.obj,.gcode`).

## 7. API Keys Page (`/keys`)

- [ ] Keys list loads and shows expected fields.
- [ ] Generate Key modal opens/closes correctly.
- [ ] Newly generated key displays once and copy-to-clipboard works.
- [ ] Revoke flow removes key from list.

Update items found in code:
- [x] Fixed key modal route button to `/api/v1/keys/create-modal`.
- [x] Fixed Jinja syntax in `fragments/keys-list.html` to use Jinja `{% else %}`.
- [x] Implemented `dateformat` filter used in `fragments/api-key-item.html`.

## 8. Profile Settings (`/settings/profile`)

- [ ] Profile data loads from `/api/v1/users/me`.
- [ ] Basic info update persists and toasts success.
- [ ] Password update validates current password and confirmation.
- [ ] Theme preference buttons work.

### Danger Zone
- [ ] Delete account action exists and is protected.

Update items found in code:
- [x] Implemented route for `DELETE /settings/account`.

## 9. Admin Area

### Admin Dashboard (`/admin`)
- [ ] Stats load from `/api/v1/admin/stats`.
- [ ] Quick-action links route correctly.

### Users (`/admin/users`)
- [ ] Users table loads.
- [ ] Add User modal create flow works.
- [ ] Edit User modal update flow works.
- [ ] Admin-only access enforced.

### Plugins (`/admin/plugins`)
- [ ] Plugins list loads.
- [ ] Upload Plugin modal opens and submit behavior is handled.

Update items found in code:
- [x] Implemented `POST /api/v1/admin/plugins/upload`.

### Settings (`/admin/settings`)
- [ ] API settings form posts and shows success/failure feedback.
- [ ] Storage settings form posts and shows success/failure feedback.
- [ ] Persisted values reload correctly after refresh.

### Logs (`/admin/logs`)
- [ ] Logs list loads on page entry.
- [ ] Level filter updates results.
- [ ] Clear logs action works and reflects empty state.

### Health (`/admin/health`)
- [ ] Health details load via HTMX.
- [ ] Metrics panel fetch succeeds and handles failures gracefully.

## 10. Dialogs, Prompts, and Ephemeral UX

Scope: modals, browser confirms, inline fragment alerts, toast notifications.

- [ ] All modal close methods work (X, Cancel, success path).
- [ ] Browser `hx-confirm` prompts appear for destructive actions.
- [ ] Server-returned error fragments render with close actions.
- [ ] Success fragments do not break page layout.
- [ ] No JavaScript console errors during modal open/submit/close loops.

## 11. Cross-Browser and Responsive

- [ ] Chromium desktop
- [ ] Firefox desktop
- [ ] WebKit/Safari-equivalent
- [ ] Mobile viewport (375x812)

## 12. Release Gate

- [ ] Critical path smoke suite passes (auth, projects CRUD, keys CRUD, admin access).
- [ ] No broken links/actions in nav, footer, and page CTAs.
- [ ] No uncaught frontend errors in browser console.
- [ ] High-severity defects triaged and fixed.
- [ ] Manual sign-off complete.