# Tasks: Directory-Based Project Storage Architecture

**Spec**: `specs/003-directory-storage-architecture/spec.md`  
**Plan**: `specs/003-directory-storage-architecture/plan.md`  
**Status**: Ready for implementation sessions

---

## How To Use This Task List

- Each task is intentionally scoped for one focused coding session.
- Complete tasks in order unless explicitly marked parallel-safe.
- A task is only complete when code + tests + verification are done.

---

## Phase 1: Data Model & Migration

### T301 - Add new project schema fields
- Update `src/backend/models/project.py`:
  - Add `slug`, `category`, `directory_path`, `disk_size_bytes`, `is_archived`
  - Keep `owner_id`, `created_at`, `updated_at`
- Ensure constraints/indexes:
  - `(owner_id, category, slug)` uniqueness or equivalent
  - index for `owner_id`

**Acceptance Criteria**
- Model imports cleanly
- Existing code paths compile and type-check

---

### T302 - Create Alembic migration 003_directory_architecture
- Add migration file in `migrations/versions/` to:
  - Add new columns to `projects`
  - Remove `description` and `custom_metadata` from `projects`
  - Drop `models` table
- Add data migration logic:
  - Generate slug/category defaults for existing rows
  - Populate `directory_path` for existing projects

**Acceptance Criteria**
- `alembic upgrade head` succeeds on clean DB
- `alembic upgrade head` succeeds on seeded DB with existing projects/models

---

### T303 - Write migration safety tests
- Add/extend tests to verify upgrade behavior:
  - Existing records survive migration
  - Directory path and slug are populated
  - Removed columns no longer referenced

**Acceptance Criteria**
- Migration tests pass consistently

---

## Phase 2: Directory & Markdown Service Layer

### T304 - Implement ProjectDirectoryService
- Create `src/backend/services/project_directory.py`:
  - `create_project_directory`
  - `list_files`
  - `read_file`
  - `write_file`
  - `delete_file`
  - `get_project_info`
  - `write_project_info`
  - `get_print_history`
  - `append_print_session`

**Acceptance Criteria**
- Service methods work in tmp filesystem tests
- No API endpoint performs direct ad-hoc filesystem operations

---

### T305 - Implement markdown parsing/rendering helpers
- Create `src/backend/services/markdown_service.py`:
  - Render markdown to HTML
  - Parse PrintHistory sessions
  - Format session entry markdown
- Add default template text for:
  - `ProjectInfo.md`
  - `PrintHistory.md`

**Acceptance Criteria**
- Parse/format round-trip tests pass for session entries
- Malformed markdown handled gracefully

---

### T306 - Add filesystem security guards
- Enforce path safety centrally:
  - Disallow path traversal (`..`), absolute paths, external symlinks
  - Sanitize filenames
  - Resolve path and verify under project root

**Acceptance Criteria**
- Security tests prove traversal attempts are rejected

---

## Phase 3: API Endpoints

### T307 - File browser API endpoints
- Update `src/backend/api/projects.py`:
  - `GET /api/v1/projects/{id}/files`
  - `GET /api/v1/projects/{id}/files/{path}`
  - `POST /api/v1/projects/{id}/files`
  - `DELETE /api/v1/projects/{id}/files/{path}`

**Acceptance Criteria**
- Upload/list/download/delete integration tests pass
- Authorization checks enforce owner-only access

---

### T308 - ProjectInfo endpoints
- Add endpoints:
  - `GET /api/v1/projects/{id}/project-info`
  - `PUT /api/v1/projects/{id}/project-info`

**Acceptance Criteria**
- Returns both raw markdown and rendered HTML
- Writes persist to `ProjectInfo.md`

---

### T309 - PrintHistory endpoints
- Add endpoints:
  - `GET /api/v1/projects/{id}/print-history`
  - `POST /api/v1/projects/{id}/print-history`
  - `GET /api/v1/projects/{id}/print-history/{session}`

**Acceptance Criteria**
- New sessions prepend to file
- Session list returns newest first

---

## Phase 4: Frontend Project Screen Redesign

### T310 - Replace model list with file browser
- Update project detail templates:
  - Replace "Loading Models..." behavior with file listing
  - Show empty state when no files exist
- Add upload control wired to file API

**Acceptance Criteria**
- Upload flow works
- No stuck loading indicator when project has no files

---

### T311 - Add ProjectInfo markdown panel/editor
- Add read + edit UI for `ProjectInfo.md`
- Save via `PUT /project-info`

**Acceptance Criteria**
- Edits persist and render correctly after save

---

### T312 - Add PrintHistory timeline UI
- Add timeline/list presentation for sessions
- Add "Log Print Session" form modal

**Acceptance Criteria**
- New entry appears immediately after submit

---

## Phase 5: Broken Screen Fixes

### T313 - Fix API Key screen loading/create flow
- Diagnose and fix key list loading state
- Fix create key submission and success handling
- Add explicit empty state message when no keys exist

**Acceptance Criteria**
- Create/list/delete keys work end-to-end
- No perpetual "Loading API Keys" state

---

### T314 - Fix Admin dashboard counts
- Fix backend stats payload and/or template mapping
- Ensure users/projects totals render correctly

**Acceptance Criteria**
- Dashboard reflects actual DB counts

---

## Phase 6: Testing & Release Prep

### T315 - Add/refresh automated tests
- Update contract/integration tests for new file/markdown APIs
- Add regression tests for prior broken screens

**Acceptance Criteria**
- Tests validate new architecture behavior

---

### T316 - Update docs and release notes
- Update:
  - `CHANGELOG.md`
  - `PROGRESS.md`
  - `README.md` (architecture section)
- Version bump after implementation completion

**Acceptance Criteria**
- Docs match implemented behavior and migration path

---

## Future Feature Set (Post-Phase)

### F301 - Print telemetry sync from markdown (non-canonical DB cache)
- Source of truth remains `PrintHistory.md`
- Add admin/manual trigger + scheduled sync job
- Write reporting cache table for analytics only

**Admin UX**
- "Sync Print Telemetry" button in admin panel
- Last-sync time and sync status indicators

**Acceptance Criteria**
- Re-sync rebuilds telemetry cache from markdown files
- Reports load from cache, never write back to markdown

---

## Suggested Session Order

1. T301 → T303
2. T304 → T306
3. T307 → T309
4. T310 → T312
5. T313 → T314
6. T315 → T316
7. F301 (future)
