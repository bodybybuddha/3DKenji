# Feature Specification: Directory-Based Project Storage Architecture

**Spec Number**: 003  
**Feature Branch**: `spec/003-directory-storage-architecture`  
**Created**: 2026-04-09  
**Status**: Approved  
**Author**: bodybybuddha  
**Supersedes**: Portions of `001-title-3d-kenji` (Model DB table, file-in-DB pattern)

---

## Overview

This spec replaces the original file-as-database-record pattern with a **directory-as-project** model.
A Project is a directory on disk. The UI is a web front-end to what users would otherwise manage manually
as a file system hierarchy. The database exists only for ownership, access control, and directory path mapping.

This design also supports mounting the storage root as a network file share (SMB/NFS) so users have a
direct file-system fallback independent of the web application.

---

## 1. Core Concepts

### 1.1 Project = Directory

Each project maps 1:1 to a directory on disk. The directory contains all project data:
markdown documentation, 3D model files, CAD source files, timelapse videos, images, and
any other supporting files the user cares to store.

### 1.2 Markdown as Content Store

Human-readable markdown files are the source of truth for project documentation and print history.
The database does **not** duplicate this content. The web UI reads and renders these files.

Canonical files for all new and managed projects are:
- `ProjectInfo.md` for project details
- `PrintHistory.md` for print sessions

Legacy structures (for example `README.md`, `readme.md`, or `Project.md` with embedded print history)
are supported only through a dedicated import utility and are not canonical in 3D Kenji storage.

### 1.3 Database = Ownership Index

The database holds the minimal set of data required to:
- Map a user to their projects
- Map a project to its directory path
- Enforce access controls
- Record when projects were created/modified

No project content is stored in the database. If the database is lost, the files on disk remain
intact and fully human-readable.

### 1.4 File-Share Fallback

The entire Projects root directory is designed to be mountable as a SMB or NFS share.
This gives users direct file access independent of the web application.

---

## 2. Directory Structure

### 2.1 Storage Root

All projects live under a single configurable root directory:

```
${STORAGE_ROOT}/
└── Projects/
    ├── {category}/
    │   └── {project-slug}/
    │       ├── ProjectInfo.md
    │       ├── PrintHistory.md
    │       ├── models/
    │       ├── cad_files/
    │       ├── timelapse/
    │       └── [any other files/directories]
    └── {another-category}/
        └── ...
```

`STORAGE_ROOT` defaults to `/data/storage` (configurable via environment variable).  
`Projects/` is a fixed subdirectory under `STORAGE_ROOT`.

### 2.2 Category

Categories are plain directory names directly under `Projects/`. They group related projects.
A project must belong to exactly one category. The default category is `Uncategorized`.

### 2.3 Project Slug

The project directory name (slug) is derived from the project title:
- Lowercase, alphanumeric and hyphens only
- Spaces replaced with hyphens
- Consecutive hyphens collapsed
- Maximum 64 characters
- Must be unique within the category

Example: "Flexi Dragon v2 (PETG)" → `flexi-dragon-v2-petg`

Slug normalization is required for all projects created and managed by 3D Kenji.
Legacy names from external directories are normalized during import.

### 2.4 Reserved Subdirectories

The following subdirectories have defined meaning in the UI:

| Directory   | Purpose                                               |
|-------------|-------------------------------------------------------|
| `models/`   | 3D print files (.stl, .3mf, .obj, .gcode, .step)     |
| `cad_files/`| Source CAD files (.f3d, .scad, .blend, .sldprt, etc.) |
| `timelapse/`| Print timelapse videos and images (.mp4, .mkv, .gif) |
| `images/`   | Project photos, reference images (.jpg, .png, .webp) |

Other directories and files at any level are supported (user-managed).

---

## 3. Markdown File Schemas

### 3.1 ProjectInfo.md

Location: `Projects/{category}/{project-slug}/ProjectInfo.md`

This is the primary project documentation file. It is created automatically when a project
is created via the web UI, pre-populated with a template. Users can edit it via the web UI
or directly in the file system.

#### Format

```markdown
# {Project Title}

## About
{Free-text description of the project}

## Source
- URL: {where the original model was downloaded from, or "Original Design"}
- License: {e.g., CC BY 4.0, Personal Use Only, Original}
- Designer: {original designer/creator credit if applicable}

## Print Profile
- Slicer: {e.g., PrusaSlicer 2.7, Bambu Studio 1.8, Cura 5.6}
- Layer Height: {e.g., 0.2mm}
- Infill: {e.g., 15% Gyroid}
- Supports: {Yes / No / Type}
- Bed Temp: {e.g., 60°C}
- Nozzle Temp: {e.g., 215°C}
- Notes: {any profile-specific notes}

## Tags
{comma-separated tags, e.g., figurine, flexi, petg, large-format}

## Notes
{Free-form notes section for anything else}

## Changelog
- {YYYY-MM-DD}: {What changed}
```

#### Rules
- All sections are optional except the title (`# {Project Title}`)
- The file is treated as standard CommonMark markdown
- The web UI can render and edit individual sections without overwriting unrecognised content
- Users may add any additional top-level sections they want; the UI will render them as-is

---

### 3.2 PrintHistory.md

Location: `Projects/{category}/{project-slug}/PrintHistory.md`

This file records every print session for the project. Each session is an H2 heading with
a fixed date format, followed by structured fields and free-form notes.

#### Format

```markdown
# Print History

## {YYYY-MM-DD} – Session {N}

- **Filament**: {Brand} {Color} ({Material}, {Diameter})
- **Duration**: {Xh Ym} (estimate or actual)
- **Printer**: {Printer name/model}
- **Result**: {Success / Failed / Partial}
- **Scale**: {100% / other}
- **Weight**: {Xg} (optional)
- **Changes from profile**: {notes or "None"}

### Notes
{Free text: what went well, what to adjust, observations}

---

## {YYYY-MM-DD} – Session {N}

{...repeat for each session...}
```

#### Rules
- Sessions are ordered newest-first (most recent at top, under the `# Print History` heading)
- The `---` horizontal rule separates sessions
- Session numbering (`Session N`) is sequential across the life of the project
- The web UI appends a new session block at the top when a user logs a print
- All bold-label fields are optional; presence is not enforced by the app
- Free-form Notes section under each session is optional but encouraged
- Users may edit the file directly; the UI re-parses on every view

---

## 4. Database Schema

### 4.1 Philosophy

The database is an **ownership and access index**, not a content store.
All content lives on disk. The database tells the app who owns what and where to find it.

### 4.2 Tables

#### `projects` (modified from existing)

| Column           | Type        | Notes                                          |
|------------------|-------------|------------------------------------------------|
| id               | UUID PK     | Stable identifier used in URLs                 |
| owner_id         | UUID FK     | References `users.id`                          |
| name             | VARCHAR(255)| Display name (also used to derive slug)        |
| slug             | VARCHAR(64) | URL/filesystem-safe version of name            |
| category         | VARCHAR(128)| Defaults to `Uncategorized`                    |
| directory_path   | VARCHAR(512)| Absolute path to project directory on disk     |
| created_at       | TIMESTAMPTZ |                                                |
| updated_at       | TIMESTAMPTZ |                                                |
| disk_size_bytes  | BIGINT      | Cached on-demand, nullable                     |
| is_archived      | BOOLEAN     | Soft-delete / archive flag; default false      |

**Removed from existing schema**: `description`, `custom_metadata` JSONB  
(This content now lives in `ProjectInfo.md`)

#### `users` (unchanged)

#### `api_keys` (unchanged)

#### `project_access` (new — future, not Phase 1)

Planned for multi-user collaboration (reader/contributor roles).  
Not implemented in Phase 1; the owner has full access and all others have none.

### 4.3 Removed Tables

- `models` table — **REMOVED**. Model files are managed as files on disk under `{project}/models/`.
  The database no longer indexes individual model files; the file browser reads the directory.

---

## 5. API Changes

### 5.1 Removed/Changed Endpoints

| Old Endpoint                              | Status    | Replacement                                   |
|-------------------------------------------|-----------|-----------------------------------------------|
| `POST /api/v1/projects/{id}/models`       | REMOVED   | `POST /api/v1/projects/{id}/files`            |
| `GET /api/v1/projects/{id}/models`        | REMOVED   | `GET /api/v1/projects/{id}/files`             |
| `GET /api/v1/models/{id}`                 | REMOVED   | `GET /api/v1/projects/{id}/files/{filename}`  |

### 5.2 New Endpoints

| Method | Path                                             | Description                                     |
|--------|--------------------------------------------------|-------------------------------------------------|
| GET    | `/api/v1/projects/{id}/files`                    | List all files in the project directory (recursive optional) |
| GET    | `/api/v1/projects/{id}/files/{path}`             | Download or stream a specific file              |
| POST   | `/api/v1/projects/{id}/files`                    | Upload one or more files to the project         |
| DELETE | `/api/v1/projects/{id}/files/{path}`             | Delete a file from the project                  |
| GET    | `/api/v1/projects/{id}/project-info`             | Return rendered ProjectInfo.md (HTML + raw)     |
| PUT    | `/api/v1/projects/{id}/project-info`             | Overwrite ProjectInfo.md content                |
| GET    | `/api/v1/projects/{id}/print-history`            | Return parsed print sessions from PrintHistory.md |
| POST   | `/api/v1/projects/{id}/print-history`            | Append a new print session entry                |
| GET    | `/api/v1/projects/{id}/print-history/{session}`  | Return a single session entry                   |

### 5.3 Unchanged Endpoints

- All auth endpoints (`/api/v1/auth/*`)
- All API key endpoints (`/api/v1/keys/*`)
- All health endpoints (`/api/v1/health/*`)
- All admin endpoints (`/api/v1/admin/*`) with additions for print-telemetry sync (see §7)
- Project CRUD (`/api/v1/projects` GET/POST/PATCH/DELETE) — updated to include `category` field

---

## 6. File Upload Rules

- Maximum file size per upload: **100 MB** (configurable via `MAX_UPLOAD_SIZE_MB`)
- Accepted types: controlled by an extension allowlist, stored in the database and editable in Admin UI
- A default allowlist is provided at first run and includes common 3D/CAD/media/doc formats
- Hidden/system files (for example `.DS_Store`) are excluded from listings by default
- Hidden/system exclusion rules are configurable in Admin UI and stored in the database
- Uploads are streamed to disk; not held in memory
- Path traversal is strictly prevented (no `..` in filenames, resolved to project dir)
- Filenames are sanitised: stripped of path separators, control characters, and leading dots
- Duplicate filenames are rejected with HTTP 409; client must delete or rename first

### 6.1 Admin-Managed File Policy

The application persists file policy in a database-backed settings model:
- extension allowlist (lowercase, dotless, unique)
- hidden/system filename patterns for exclusion in UI/API list views
- optional per-role override behavior for future use (not Phase 1)

Admin pages provide CRUD operations for these settings. Changes apply without restart.

### 6.2 Minimal Settings Schema (Phase 1)

Use a single generic settings table for admin-configurable app policies.

#### `app_settings`

| Column      | Type         | Notes                                               |
|-------------|--------------|-----------------------------------------------------|
| id          | UUID PK      |                                                     |
| key         | VARCHAR(128) | Unique setting key                                  |
| value_json  | JSONB        | Structured setting payload                          |
| updated_by  | UUID FK      | References `users.id` (admin actor)                |
| updated_at  | TIMESTAMPTZ  | Last update timestamp                               |

Required keys in Phase 1:
- `file_policy.allowed_extensions`
- `file_policy.hidden_name_patterns`
- `file_policy.max_upload_size_mb` (optional override of env default)

Recommended default values:
- `file_policy.allowed_extensions`:
  - `stl`, `3mf`, `obj`, `step`, `stp`, `f3d`, `f3z`, `fcstd`, `fcbak`, `scad`, `blend`
  - `jpg`, `jpeg`, `png`, `webp`, `gif`, `mp4`, `mkv`, `avi`, `md`, `txt`, `pdf`
- `file_policy.hidden_name_patterns`:
  - `.DS_Store`, `Thumbs.db`, `desktop.ini`, `._*`, `*.tmp`

### 6.3 Admin API Contract (Minimal)

All endpoints are admin-only and return JSON.

| Method | Path                                      | Description |
|--------|-------------------------------------------|-------------|
| GET    | `/api/v1/admin/settings/file-policy`      | Get effective file policy |
| PUT    | `/api/v1/admin/settings/file-policy`      | Replace file policy settings |
| POST   | `/api/v1/admin/settings/file-policy/reset`| Reset to default file policy |

`GET /api/v1/admin/settings/file-policy` response:

```json
{
  "allowed_extensions": ["stl", "3mf", "mp4"],
  "hidden_name_patterns": [".DS_Store", "Thumbs.db", "._*"],
  "max_upload_size_mb": 100,
  "updated_at": "2026-04-09T18:00:00Z",
  "updated_by": "<admin-user-id>"
}
```

`PUT /api/v1/admin/settings/file-policy` request body:

```json
{
  "allowed_extensions": ["stl", "3mf", "obj", "mp4"],
  "hidden_name_patterns": [".DS_Store", "Thumbs.db", "._*"],
  "max_upload_size_mb": 100
}
```

Validation rules:
- `allowed_extensions`:
  - required non-empty array
  - lowercase strings only
  - dotless extension format (`stl`, not `.stl`)
  - unique values after normalization
- `hidden_name_patterns`:
  - required array
  - supports simple wildcard patterns (`*`, `?`)
  - max 128 patterns
- `max_upload_size_mb`:
  - integer, minimum 1, maximum 2048

Error contract:
- `400` invalid payload or invalid pattern syntax
- `401` unauthenticated
- `403` authenticated but not admin
- `409` optimistic concurrency conflict (if versioning is enabled)

### 6.4 Runtime Enforcement Rules

- Upload validation checks file extension against `allowed_extensions`.
- File listing applies `hidden_name_patterns` by default.
- Optional list query parameter `include_hidden=true` is admin-only.
- Policy is read-through cached for performance with short TTL and explicit cache bust on update.
- On missing settings rows, service falls back to safe defaults and logs a warning.

---

## 7. Print Telemetry (Future Feature)

### 7.1 Concept

Print session data lives in `PrintHistory.md` files. The database does **not** duplicate this.
However, a future admin function will allow:
1. A scheduled background task (e.g., nightly) that scans all `PrintHistory.md` files
2. A manual "Sync Print Telemetry" button in the Admin panel
3. Both write aggregate statistics to a read-only `print_telemetry_cache` table

### 7.2 Cache Table (Future, not Phase 1)

| Column          | Type         | Notes                                        |
|-----------------|--------------|----------------------------------------------|
| id              | UUID PK      |                                              |
| project_id      | UUID FK      |                                              |
| session_date    | DATE         | Parsed from `## YYYY-MM-DD – Session N`      |
| session_number  | INTEGER      |                                              |
| filament_brand  | VARCHAR(128) | Parsed from "Filament" field                 |
| filament_material| VARCHAR(64) | Parsed from "Filament" field                 |
| filament_color  | VARCHAR(64)  | Parsed from "Filament" field                 |
| duration_minutes| INTEGER      | Parsed from "Duration" field                 |
| result          | VARCHAR(32)  | Success / Failed / Partial                   |
| synced_at       | TIMESTAMPTZ  | When this scan ran                           |

This table is **read-only from the UI** (reports only). Source of truth remains markdown.

### 7.3 Admin Trigger for Sync (Future)

- `POST /api/v1/admin/sync-print-telemetry` — triggers a scan (admin only)
- Scheduled task: configurable cron expression via env var `TELEMETRY_SYNC_CRON`
- Sync is idempotent: re-scans rebuild the table from scratch

---

## 8. Storage Backend Abstraction

The storage layer is abstracted behind a `StorageBackend` interface (already exists in the plugin system).
Phase 1 implements `LocalStorageBackend`. Future backends:

| Backend               | Priority  |
|-----------------------|-----------|
| Local filesystem      | Phase 1   |
| Amazon S3             | Future    |
| Azure Blob Storage    | Future    |
| Google Cloud Storage  | Future    |

Backend selection is via `STORAGE_BACKEND` environment variable.

---

## 9. Security Considerations

- All file paths are resolved and validated to remain within `${STORAGE_ROOT}/Projects/`
- Project directory paths stored in DB are validated on every access (prevent symlink attacks)
- No shell execution for file operations (pure Python `pathlib` / `shutil`)
- File uploads are written atomically to a temp file, then moved (prevents partial writes)
- Admin-only endpoints for telemetry sync enforce `is_admin` check
- No direct URL access to raw files outside of authenticated API endpoints

---

## 10. Migration from Current Schema

The existing `models` table will be dropped. Existing model file paths stored in the DB
will be used to copy files into the new directory structure during migration.

Migration steps (Alembic `003_directory_architecture.py`):
1. Add `slug`, `category`, `directory_path`, `disk_size_bytes`, `is_archived` to `projects`
2. Remove `description`, `custom_metadata` from `projects` (content moves to `ProjectInfo.md`)
3. Create `Projects/` directory structure for all existing projects
4. Write `ProjectInfo.md` for each project with description/metadata from DB
5. Copy existing model files into `{project}/models/`
6. Drop `models` table

---

## 11. User Scenarios

1. **Create Project**: User fills in title + category → directory created, `ProjectInfo.md` pre-populated from template
2. **Browse Files**: User opens project → sees file browser listing directory contents with icons by type
3. **Upload Model**: User clicks upload, selects STL → file placed in `models/` subdirectory
4. **Edit ProjectInfo**: User clicks edit on ProjectInfo panel → markdown editor opens, saves to disk
5. **Log a Print**: User clicks "Log Print Session" → form fields → appended to `PrintHistory.md`
6. **View Print History**: User opens history tab → ParsedHistory.md rendered as a timeline
7. **Direct File Access**: User mounts `Projects/` as SMB share → browses with Windows Explorer
8. **Admin Telemetry Sync**: Admin clicks "Sync Print Telemetry" → all PrintHistory.md files parsed → dashboard shows aggregate stats
9. **Preview STL**: User selects an STL file → inline 3D preview renders in project page viewer panel
10. **Preview Timelapse Video**: User selects a timelapse video → inline video player opens and streams media

---

## 12. Legacy Import Utility (Outside Main Repo, Future)

An external utility will import legacy directory structures into canonical 3D Kenji layout.

### 12.1 Import Rules

- Input may contain legacy docs (`README.md`, `readme.md`, `Project.md`) and mixed files
- Output must be canonical (`ProjectInfo.md` + `PrintHistory.md`)
- Print history embedded in legacy docs is extracted into `PrintHistory.md`
- Project slugs are normalized per section 2.3
- Project detection is **leaf-only**: only leaf candidate directories are imported as projects
- Legacy dates may be parsed from common formats during import, but all new writes use `YYYY-MM-DD`

### 12.2 Conflict Handling

- Name/path collisions are interactive (`prompt`) in the import tool
- Tool supports non-interactive mode in future (out of scope for initial importer)

### 12.3 Execution Model

- Import is best-effort per run (does not rollback entire run on one failure)
- Tool produces a final report with:
  - successful imports
  - skipped items
  - failed items with error reasons
  - manual follow-up recommendations

### 12.4 Nice-to-Have

- Dry-run mode that emits a move/transform manifest without writing files

---

## 13. Out of Scope (This Spec)

- Multi-user collaboration and project sharing (deferred)
- Project templates configurable by admins (deferred)
- S3/Azure storage backends (deferred)
- OAuth authentication (deferred)
