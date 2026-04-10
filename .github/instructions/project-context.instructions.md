---
description: "Use when working in the 3DKenji repository and project-level context is needed. Covers architecture, stack, and high-level workflow expectations for FastAPI, PostgreSQL, plugins, and filesystem-backed project metadata."
name: "3DKenji Project Context"
---
# 3DKenji Project Context

- 3DKenji is a FastAPI backend with hybrid storage:
  - PostgreSQL stores identity, ownership, and relational metadata.
  - Filesystem under `STORAGE_ROOT` stores project artifacts and markdown metadata files.
- Key backend code is under `src/backend/`.
- Key tests are under `tests/` with contract, integration, validation, and e2e layers.
- Database evolution uses Alembic migrations under `migrations/`.

## Core Working Rules

- Prefer small, focused changes over broad refactors.
- Preserve existing API contracts unless behavior change is explicitly requested.
- Keep database model changes and migrations synchronized.
- Keep filesystem/frontmatter behavior backward compatible unless migration guidance is included.
- Run relevant tests for changed behavior and report what was validated.
