# Implementation Plan: 3D Kenji Core: Projects & Models

**Branch**: `001-title-3d-kenji` | **Date**: 2025-09-07 | **Spec**: `spec.md`
**Input**: Feature specification from `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/spec.md`

## Summary
Implement an API-first backend and initial Flask/Jinja2 frontend to manage Projects, Models, Media, PrintJobs, Notes (Markdown). Use Python 3.11, FastAPI for the API, SQLAlchemy + Alembic for DB models/migrations, PostgreSQL with JSONB for flexible metadata, and pytest for tests. Containerize services and provide devcontainer + docker-compose for local development.

## Technical Context
Language/Version: Python 3.11
Primary Dependencies: FastAPI (API), Flask+Jinja2 (web UI), SQLAlchemy, Alembic, pytest, uvicorn, psycopg[binary]
Storage: PostgreSQL (JSONB for flexible fields), object storage for media (local by default, S3-compatible optional)
Testing: pytest (contract, integration, unit), tox optional
Target Platform: Linux containers (lightweight base image like python:3.11-slim or debian-based variant)
Project Type: Web application (backend API + optional server-rendered frontend)
Performance Goals: NFRs TBD; initial target: handle small teams and hobbyist usage (low concurrency)
Constraints: All work in devcontainers; reproducible Docker images; migrations via Alembic.

## Constitution Check

Simplicity: Project uses a clear web/backend split. Core libraries for models/services will be created. No unnecessary abstraction layers.

Architecture: Each major capability (projects, models, media, auth) will be written as a reusable Python package/module within `backend/src/`.

Testing (NON-NEGOTIABLE): TDD workflow enforced. Contract tests (from OpenAPI) will be written first and expected to fail. CI must run contracts, integration, and unit tests.

Observability: Structured JSON logging to files by default; configurable sinks.

Versioning: Semantic versioning; migration guides required for breaking changes.

## Phase 0: Outline & Research (research.md)
See `research.md` for decisions and open items. Primary resolved items below:

- Chosen web API framework: FastAPI (better for OpenAPI-first workflows). Flask retained for server-side convenience pages.
- Media storage: default to local filesystem under configured mount (e.g., `/data/media`); design to allow S3-compatible backends via an abstraction layer.
- Auth: support username/password + OAuth via reusable library (e.g., Authlib) and scoped API keys stored hashed in DB.
- Model file types: support .stl, .3mf, .obj, .gcode as initial whitelist; configurable by admins.
- Max file size: default 100MB; configurable via deployment env; large-file workflows may use chunked uploads in future.

## Phase 1: Design & Contracts

Artifacts to generate here (created as stubs):
- `data-model.md` — entity definitions and fields (created)
- `contracts/openapi.yaml` — OpenAPI skeleton for core endpoints (created)
- `quickstart.md` — how to run in devcontainer and run tests (created)

### API Contract decisions (high level)
- RESTful endpoints under `/api/v1` with JSON request/response
- Security schemes: `cookieAuth` for session-based UI + `ApiKeyAuth` (header) for scoped keys; OAuth flows documented in OpenAPI securitySchemes
- Resources: /projects, /projects/{id}/models, /models/{id}, /projects/{id}/notes, /keys

### Testing Strategy
- Contract tests generated from `contracts/openapi.yaml` and placed in `tests/contract/` (failing initially)
- Integration tests: use a docker-compose test environment with Postgres; place in `tests/integration/`

## Phase 2: Task Planning Approach
(Describes `/tasks` behavior — not executed here.)

## Progress Tracking
- [x] Phase 0: Research complete
- [x] Phase 1: Design complete (stubs created)
- [ ] Phase 2: Task planning described (this command does not create tasks.md)

## Output paths
- FEATURE_SPEC: `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/spec.md`
- IMPL_PLAN: `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/plan.md`
- SPECS_DIR: `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji`

---

Next actions (recommended):
1. Review `contracts/openapi.yaml` for completeness; confirm auth/security choices.
2. Run `/scripts/tasks.sh` (or `/tasks` command) to generate tasks.md.
3. Begin implementation by creating failing contract tests and scaffolding models/services.
