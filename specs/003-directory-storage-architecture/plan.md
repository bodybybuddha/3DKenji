# Implementation Plan: Directory-Based Project Storage Architecture

**Branch**: `spec/003-directory-storage-architecture`  
**Date**: 2026-04-09  
**Spec**: `spec.md`  
**Version**: 1.2.0 (target release after all phases complete)

---

## Summary

Redesign 3D Kenji from a database-centric model storage approach to a
directory-based project management system. Projects are directories on disk;
markdown files are the source of truth for content; the database is a minimal
ownership and access-control index.

This is a **breaking architectural change** requiring:
- A new database migration (003)
- Rewritten backend services for projects and files
- New API endpoints for file browsing, markdown read/write, print history
- Redesigned frontend screens for project detail, file browser, and print history
- Fixes to all currently broken screens as a natural outcome of the rewrite

---

## Guiding Principles

1. **Files first** — All project content lives on disk in human-readable form.
2. **DB is minimal** — Only ownership, path mapping, and access control in the DB.
3. **Backwards-compatible fallback** — The Projects directory can be mounted as SMB/NFS at any time.
4. **One feature per session** — Each phase section is sized to be completable in one coding session.
5. **Test before ship** — Each task includes tests before the feature is considered done.
6. **Future-proof** — Storage backend stays abstracted; print telemetry deferred but designed in.

---

## Technical Context

| Item               | Decision                                                    |
|--------------------|-------------------------------------------------------------|
| Language           | Python 3.11                                                 |
| API Framework      | FastAPI                                                     |
| Templates          | Jinja2 (server-rendered, HTMX for interactions)            |
| Database           | PostgreSQL via SQLAlchemy + Alembic                         |
| File I/O           | Python `pathlib` / `shutil` — no shell execution           |
| Markdown           | `python-markdown` or `mistune` for server-side rendering   |
| Storage (Phase 1)  | Local filesystem under `${STORAGE_ROOT}/Projects/`         |
| Storage (Future)   | Pluggable backends: S3, Azure Blob                         |
| Testing            | pytest (unit + integration); validation tests for security |
| Container          | Docker + docker-compose, devcontainer for dev              |

---

## Phase Overview

| Phase | Name                          | Sessions | Depends On   |
|-------|-------------------------------|----------|--------------|
| P0    | Planning & Approval           | 1        | —            |
| P1    | Data Model & Migration        | 1        | P0           |
| P2    | Storage Service Layer         | 1        | P1           |
| P3    | File & Markdown APIs          | 2        | P2           |
| P4    | Project Screen Redesign       | 2        | P3           |
| P5    | Print History Screen          | 1        | P3           |
| P6    | Fix: API Key Screen           | 1        | P1           |
| P7    | Fix: Admin Dashboard          | 1        | P1           |
| P8    | Polish & Testing              | 1        | P4–P7        |
| F1    | Future: Print Telemetry Sync  | 1        | P5 + P8      |
| F2    | Future: S3/Azure Backends     | 2        | P2           |
| F3    | Future: OAuth Plugins         | 2        | P8           |

---

## Phase 0: Planning & Approval ✅ COMPLETE

**Goal**: Document architecture, get owner approval before code changes.

**Outputs**:
- `specs/003-directory-storage-architecture/spec.md` ✅
- `specs/003-directory-storage-architecture/plan.md` ✅ (this file)
- `specs/003-directory-storage-architecture/tasks.md` ✅

**Decision log**:
- ✅ ProjectInfo.md (not README.md) as primary project document
- ✅ PrintHistory.md as single file with per-session entries (newest first)
- ✅ Single `Projects/` root for all projects (SMB/NFS mountable)
- ✅ Categories as plain subdirectories
- ✅ Slug normalization is required for managed projects
- ✅ DB role: ownership + path index only (no content)
- ✅ `models` table removed; files managed on disk
- ✅ Legacy import utility will be external to this repo
- ✅ Legacy import uses leaf-only project detection, interactive collision prompts, and best-effort execution
- ✅ File extension allowlist + hidden/system file exclusions configurable from Admin and stored in DB
- ✅ Print session dates standardized on write (`YYYY-MM-DD`)
- ✅ Inline STL and timelapse video previews required on project page
- ✅ Print telemetry deferred to Future phase (admin sync from markdown)
- ✅ Multi-backend storage abstraction maintained

---

## Phase 1: Data Model & Migration

**Goal**: Update the database schema. Migrate existing data. No screen changes.

**What changes**:
- `projects` table: add `slug`, `category`, `directory_path`, `disk_size_bytes`, `is_archived`
- `projects` table: remove `description`, `custom_metadata`
- Add settings persistence for upload policy and hidden/system exclusion patterns
- `models` table: removed (data migrated to filesystem)
- Alembic migration `003_directory_architecture.py` created and tested
- ProjectService updated for new schema (no file logic yet — that's Phase 2)

**New files**:
- `migrations/versions/003_directory_architecture.py`
- `src/backend/models/project.py` (updated)
- `src/backend/models/system_setting.py` (or equivalent app settings model)

**Tests**:
- Migration runs forward cleanly on fresh DB
- Migration runs forward on DB with existing test data (migration test)
- `project.slug` is computed correctly from title
- Existing projects get valid `directory_path` assigned
- Settings defaults seeded for extension allowlist and hidden/system exclusions

**Session size**: ~3–4 hours

---

## Phase 2: Storage Service Layer

**Goal**: Implement the `ProjectDirectory` service that abstracts all file operations.
APIs and frontend use this service — they never touch the filesystem directly.

**What's built**:
- `src/backend/services/project_directory.py` — `ProjectDirectoryService`
  - `create_project_directory(project)` — mkdir + initial files
  - `list_files(project, path='')` — returns tree/list of files
  - `read_file(project, path)` — returns file bytes/stream
  - `write_file(project, path, content)` — writes, validates path
  - `delete_file(project, path)` — removes a file
  - `get_project_info(project)` — reads + parses ProjectInfo.md
  - `write_project_info(project, content)` — saves ProjectInfo.md
  - `get_print_history(project)` — reads + parses PrintHistory.md
  - `append_print_session(project, session_data)` — prepends new entry to PrintHistory.md
- `src/backend/services/markdown_service.py` — pure functions for parse/render
  - `render_markdown(text)` → HTML string
  - `parse_print_history(text)` → list of session dicts
  - `format_print_session(data)` → markdown string for one session
- ProjectInfo.md and PrintHistory.md templates (string constants or files)

**Security enforcement** (all in `ProjectDirectoryService`):
- Every path is resolved with `pathlib.Path.resolve()` and checked to be within project dir
- No `..` traversal, no absolute paths, no symlinks outside project dir
- Filenames sanitised before any write

**Tests**:
- Unit tests for all `ProjectDirectoryService` methods (mock filesystem or tmp dir)
- Unit tests for all `markdown_service` parse/format functions
- Security tests: path traversal attempts return 400/reject
- Edge cases: empty PrintHistory.md, malformed session entries

**Session size**: ~4–5 hours

---

## Phase 3: File & Markdown API Endpoints

**Goal**: Expose the storage service layer via FastAPI endpoints. Two sub-sessions.

### Phase 3A: File Browser API

**What's built**:
- `GET /api/v1/projects/{id}/files` — list files (JSON + HTML fragment)
- `GET /api/v1/projects/{id}/files/{path}` — download/stream file
- `POST /api/v1/projects/{id}/files` — upload file (multipart)
- `DELETE /api/v1/projects/{id}/files/{path}` — delete file
- File type detection for icons (client hints based on extension)

**Tests**:
- Upload STL → appears in listing
- Upload to `models/` subdirectory
- Download file → correct bytes returned
- Delete file → gone from listing
- Path traversal via upload filename → rejected 400
- Unauthenticated access → 401
- Another user's project → 403

**Session size**: ~3 hours

### Phase 3B: Markdown API (ProjectInfo + PrintHistory)

**What's built**:
- `GET /api/v1/projects/{id}/project-info` — returns `{raw: "...", html: "..."}`
- `PUT /api/v1/projects/{id}/project-info` — overwrites ProjectInfo.md
- `GET /api/v1/projects/{id}/print-history` — returns list of parsed sessions
- `POST /api/v1/projects/{id}/print-history` — appends new session to PrintHistory.md
- `GET /api/v1/projects/{id}/print-history/{session_n}` — single session

**Tests**:
- ProjectInfo renders correctly from known markdown
- PUT ProjectInfo persists and re-reads correctly
- PrintHistory parse returns ordered sessions
- Append new session appears at top of file
- Session write path always normalizes date to `YYYY-MM-DD`
- Malformed PrintHistory.md handled gracefully (no crash)

**Session size**: ~3 hours

---

## Phase 4: Project Screen Redesign

**Goal**: Rebuild the project detail page to show file browser, ProjectInfo, and print history.
Two sub-sessions due to HTMX complexity.

### Phase 4A: Project Detail Layout + File Browser

**What's built**:
- `src/frontend/templates/project-detail.html` — three-panel layout:
  - Left: file browser tree
  - Right-top: ProjectInfo.md rendered
  - Right-bottom: Print History tab (stub)
- `src/frontend/templates/fragments/file-browser.html` — HTMX file list fragment
- File type icons (via CSS classes or inline SVG)
- "Upload File" button and drag-drop zone (basic)

**Fixes automatically**:
- "Loading Models..." spinner that never resolves → replaced by file browser
- "+Upload Model" button that did nothing → new upload flow in place

**Session size**: ~4 hours

### Phase 4B: ProjectInfo Editor + Create Project Form

**What's built**:
- Inline markdown editor for ProjectInfo.md (textarea + preview toggle)
- "Save" button triggers `PUT /api/v1/projects/{id}/project-info`
- Create project form updated: adds `category` dropdown + auto-slug preview
- Edit project title/category updates directory path (rename handling)

**Tests (integration)**:
- Create project → directory created → ProjectInfo.md exists
- Edit ProjectInfo via UI → file on disk updated
- Create project with category → appears under correct directory

**Session size**: ~3 hours

---

## Phase 5: Print History Screen

**Goal**: Display and add print sessions.

**What's built**:
- `src/frontend/templates/fragments/print-history.html` — timeline of sessions
- "Log Print Session" modal form with fields: date, filament, duration, printer, result, notes
- Submits `POST /api/v1/projects/{id}/print-history`
- List auto-refreshes via HTMX after submit
- Sessions shown with date, filament, result (expandable for full notes)

**Tests**:
- Log a session → appears in history list
- Multiple sessions → correct order (newest first)
- Form validation (date required)

**Session size**: ~3 hours

---

## Phase 6: Fix API Key Screen

**Goal**: Fix the currently broken API key management page.

**Known issues** (from user report and logs):
- "Loading API Keys..." spinner that never resolves
- "Create API Key" form non-functional

**Investigation first** (~30 min):
- Trace the HTMX request from the API key page
- Identify if backend endpoint, frontend template, or JS auth token is the failure point

**What's fixed**:
- Correct the HTMX endpoint or response format for key listing
- Fix the create-key form submission
- Ensure empty state shows a proper "No API keys yet" message (not a spinner)
- Display created key secret in a copy-to-clipboard modal (shown once)

**Session size**: ~2–3 hours

---

## Phase 7: Fix Admin Dashboard

**Goal**: Fix the admin dashboard showing blank stats (users: blank, projects: `-`).

**Known issues** (from user report):
- User count not displaying despite dummy users in DB
- Project count showing `-` despite existing projects

**Investigation first** (~30 min):
- Check `/api/v1/admin/stats` response against what the template expects
- Identify field name mismatch or missing query

**What's fixed**:
- Admin stats API returns correct counts from database
- Dashboard template binds to correct field names
- Add: disk usage summary per user (reads from directory sizes)
- Add: file policy admin page/subpage for extension allowlist + hidden/system exclusions

**Session size**: ~2 hours

---

## Phase 7B: Media Preview (STL + Timelapse)

**Goal**: Add inline preview capability in project pages for STL files and timelapse videos.

**What's built**:
- STL preview panel (client-side viewer) for `.stl`
- Inline video player for supported timelapse formats (at least `.mp4`, configurable)
- Graceful fallback for non-previewable files (download/open only)

**Tests**:
- Selecting `.stl` shows 3D preview without full-page navigation
- Selecting timelapse video streams in embedded player
- Unsupported format falls back cleanly without UI breakage

**Session size**: ~3 hours

---

## Phase 8: Polish, Testing & Release

**Goal**: Final integration testing, cleanup, and 1.2.0 release preparation.

**What's done**:
- End-to-end test: create project → upload model → log print → view history
- Update CHANGELOG.md with v1.2.0
- Update PROGRESS.md
- Update pyproject.toml version to `1.2.0`
- Clear TODO.md completed items
- Run full test suite; ensure 0 failures
- Update BUGS.md: close any bugs fixed in this work

**Session size**: ~2 hours

---

## Future Phase F1: Print Telemetry Sync (Admin)

**Goal**: Parse all `PrintHistory.md` files across all projects and populate a reportable cache table.

**What's built**:
- `print_telemetry_cache` DB table (see spec §7.2)
- `POST /api/v1/admin/sync-print-telemetry` endpoint (admin only)
- Background task via APScheduler or simple asyncio task (configurable cron)
- Admin dashboard "Print Stats" panel: filament usage, success rate, total print time

**Design rule**: Cache is always rebuilt from markdown (never canonical). If markdown changes, re-sync.

**Session size**: ~4 hours

---

## Future Phase F2: S3 / Azure Storage Backends

**Goal**: Allow `Projects/` to be stored in S3 or Azure Blob instead of local disk.

**Note**: Requires design work on how file browsing and streaming work for remote storage.
Spec update required before implementation.

---

## Future Phase F3: OAuth Plugins (GitHub, Google)

**Goal**: Allow users to sign in with GitHub or Google OAuth in addition to username/password.

**Requires**: OAuth provider plugin interface (already partially designed in spec 002).

---

## Future Phase F4: External Legacy Import Utility

**Goal**: Build an external utility to import legacy project directories into canonical 3D Kenji layout.

**Requirements**:
- Converts legacy markdown layouts into `ProjectInfo.md` and `PrintHistory.md`
- Uses leaf-only project detection
- Uses interactive prompt behavior for collisions
- Runs in best-effort mode and emits end-of-run report for skipped/failed items
- Supports dry-run manifest mode (nice-to-have)

---

## Risk Register

| Risk                                        | Likelihood | Impact | Mitigation                                              |
|---------------------------------------------|------------|--------|---------------------------------------------------------|
| Existing model files lost during migration  | Low        | High   | Migration copies files before dropping table; tested   |
| Path traversal security gap in file upload  | Medium     | High   | All paths resolved + validated in service layer        |
| PrintHistory.md parse fails on user edits   | Medium     | Medium | Graceful fallback; show raw markdown if parse error    |
| Directory rename breaks DB path reference   | Medium     | Medium | Phase 4B handles rename; path stored in DB updated     |
| Performance: large directories slow browser | Low        | Medium | Paginate file listing; optional lazy-load              |
| STL/video preview performance on large files| Medium     | Medium | Lazy load viewer; stream media; cap preview size       |
