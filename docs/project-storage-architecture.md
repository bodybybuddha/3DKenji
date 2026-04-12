---
layout: default
title: Project Storage Architecture
---

# Project Storage Architecture

This document describes the current filesystem-backed project model with frontmatter-based metadata and related markdown files.

## Overview

Projects are represented in two places:

1. **Database metadata** (owner, title, slug, category, timestamps, permissions)
   - Source of truth for identity, ownership, and system state
2. **Filesystem directory** rooted at `STORAGE_ROOT`
   - Source of truth for project artifacts and human-editable metadata

The hybrid model uses:
- Database as canonical for access control and system lifecycle events
- Filesystem as canonical for user-editable project documentation and metadata
- YAML-like frontmatter in markdown files for structured metadata
- Markdown body for human-readable freeform content

## Storage Root

Environment variable:

- `STORAGE_ROOT` (default: `/data/storage`)

Project directories are created under:

- `STORAGE_ROOT/Projects/<owner_nickname>/<slug>`

Examples:

- `/data/storage/Projects/alice-prints/test-project-1`
- `/data/storage/Projects/admin/showcase-gearbox`

## Visibility and Category

- Project visibility is represented separately from category:
  - `visibility`: `private` or `public`
  - `category`: freeform organizational label (defaults to `Uncategorized`)

Current lifecycle behavior:

- Archived projects keep owner-scoped storage paths and are marked `is_archived = true` in database state.

## Compatibility and Path Resolution

To preserve compatibility with existing installations, services resolve project directories in this order:

1. `Projects/<owner_nickname>/<slug>` (canonical)
2. `Projects/<owner_id>/<slug>` (legacy owner-id path)
3. `Projects/<category>/<slug>` (legacy category path)

The canonical path is persisted in project `directory_path` as `Projects/<owner_nickname>/<slug>`.

## Project Directory Layout

Each project directory is seeded with this structure:

- `ProjectInfo.md` (frontmatter + markdown body)
- `PrintHistory.md` (frontmatter + session entries)
- `models/`
- `cad_files/`
- `timelapse/`
- `images/`

## Frontmatter-Based Metadata

All markdown files in projects now use YAML-like frontmatter (delimited by `---`) to store structured metadata, followed by a markdown body for human-editable content.

Frontmatter features:

- Minimal YAML-like syntax (no external dependencies required)
- Supports scalar values and list entries
- Automatically parsed and separated from markdown body
- Preserved exactly by rendering services (frontmatter never appears in HTML output)
- Backward compatible: existing markdown files are automatically upgraded to include frontmatter

### Frontmatter Format

```yaml
---
key1: value1
key2: value2
list_key:
  - item1
  - item2
---

# Markdown body starts here
```

## ProjectInfo.md Format

`ProjectInfo.md` combines structured metadata with human-readable project documentation.

### Frontmatter Schema

| Key | Type | Example | Notes |
|-----|------|---------|-------|
| `title` | string | "My Awesome Widget" | Project name (canonically in DB) |
| `summary` | string | "A handy device for..." | Short project summary |
| `tags` | list | `["3d-printing", "calibration"]` | Project categories/labels |
| `designer` | string | "John Smith" | Original designer/source attribution |
| `source_url` | string | "https://example.com/project" | Link to original design source |
| `license` | string | "CC BY-SA 4.0" | License of the design |
| `status` | string | "active" | `active`, `completed`, `archived`, or `abandoned` |

### Markdown Body Structure

Default sections include:

- `# About` – Project overview and intended use
- `## Print Profile` – Default print settings and assumptions
- `## Notes` – General project notes and observations
- `## Changelog` – Record of significant changes and print iterations

Expected usage:

- Keep project-level intent and provenance in metadata
- Track meaningful changes in the changelog section
- Capture print profile assumptions that should survive model revisions

### Seeding Example

```markdown
---
title: Example Project
summary: A useful tool for the workshop
tags:
  - 3d-printing
  - tools
designer: Jane Doe
source_url: https://printables.com/model/123
license: CC BY-SA 4.0
status: active
---

# About
This project creates a handy organizer for my desk...

## Print Profile
- Slicer: Prusaslicer 2.4
- Layer Height: 0.2mm
- Infill: 15% Gyroid
- Supports: No
- Bed Temp: 60°C
- Nozzle Temp: 210°C
- Notes: Works best with PLA

## Notes
- First print was a success!
- Consider chamfering the edges in next revision

## Changelog
- 2026-04-10: Project created
- 2026-04-08: Added draft CAD files
```

## PrintHistory.md Format

`PrintHistory.md` documents all print sessions for the project with file-level metadata and per-session details.

### Frontmatter Schema

| Key | Type | Example | Notes |
|-----|------|---------|-------|
| `project` | string | "My Widget" | Project name for reference |
| `created_date` | string | "2026-01-15" | Date history file was created |
| `last_print_date` | string | "2026-04-10" | Most recent print session date |
| `total_sessions` | string | "12" | Total number of print sessions |
| `printer_model` | string | "Prusa i3 MK3" | Default printer for this project |
| `notes` | string | "Observing layer shift issues recently..." | General notes about print history |

### Session Entry Format

Each print session is recorded as a level-2 heading with structured fields:

```markdown
## YYYY-MM-DD – Session N

- **Filament**: material identAnd settings
- **Result**: Success / Partial / Failed
- **Duration**: time taken
- **Printer**: printer model used
- **Scale**: 100%  (default)
- **Weight**: final weight (optional)
- **Changes from profile**: deviations noted

### Notes
Optional session-specific notes and observations.

---
```

Session numbering is auto-assigned as `(existing_sessions) + 1`.

### Complete Example

```markdown
---
project: Test Widget Organizer
created_date: 2026-01-15
last_print_date: 2026-04-10
total_sessions: 3
printer_model: Prusa i3 MK3
notes: Main organizer project; tracking layer shift issues from session 2
---

# Print History

## 2026-04-10 – Session 3

- **Filament**: Prusament PLA Black
- **Duration**: 4h 23m
- **Printer**: Prusa i3 MK3
- **Result**: Success
- **Scale**: 100%
- **Changes from profile**: None

### Notes
Clean print, no layer shift observed. Issue from session 2 appears resolved.

---

## 2026-03-25 – Session 2

- **Filament**: Prusament PLA Grey
- **Duration**: 3h 45m
- **Printer**: Prusa i3 MK3
- **Result**: Partial
- **Scale**: 100%
- **Changes from profile**: Reduced nozzle temp to 205°C

### Notes
Layer shift at 1h 30m into print. Possible bearing wear. Investigate before session 3.

---

## 2026-01-20 – Session 1

- **Filament**: Prusament PLA White
- **Duration**: 5h 12m
- **Printer**: Prusa i3 MK3
- **Result**: Success
- **Scale**: 100%
- **Changes from profile**: None

### Notes
First prototype print. All dimensions within tolerance.

---
```

## Lifecycle Rules (Current)

Create project:

- Create DB row with computed `slug`, `category`, `visibility`, and owner-scoped `directory_path`
- Create filesystem directory and seed markdown files

Update project title/category:

- Update DB metadata
- Move/rename filesystem directory only when slug/path changes

Update nickname:

- User nickname changes trigger owner-root migration from old owner segment to new segment
- All owned project `directory_path` values are updated to the new owner segment
- Migration is applied with rollback protection when DB commit fails

Delete project:

- Default archive behavior marks project archived while preserving owner-scoped directory
- Hard-delete policy removes project and filesystem directory

## Backfill and Migration

Use the backfill utility to migrate existing project directories into owner-scoped layout and normalize frontmatter files:

```bash
python scripts/backfill-project-filesystem.py --dry-run
python scripts/backfill-project-filesystem.py --apply
```

The script:

- Detects legacy directory candidates from historical `directory_path` values
- Moves directories into canonical owner-segment paths
- Repairs `directory_path` values in database
- Seeds missing `ProjectInfo.md` and `PrintHistory.md`
- Upgrades frontmatter for existing markdown files

## Operational Guidance

To keep paths predictable across environments:

- Always set `STORAGE_ROOT` explicitly in runtime environment
- In development, prefer a workspace path, for example:
  - `STORAGE_ROOT=/workspace/data/storage`
- In production, map `STORAGE_ROOT` to a persistent volume

## Verification Checklist

When validating project creation:

1. Confirm DB row has `directory_path = Projects/<owner_nickname>/<slug>`
2. Confirm directory exists under `STORAGE_ROOT`
3. Confirm `ProjectInfo.md` and `PrintHistory.md` exist
4. Confirm default subdirectories exist
