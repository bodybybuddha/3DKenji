# Tasks: 3D Kenji Core: Projects & Models

**Input**: Design documents from `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/`
**Prerequisites**: `plan.md`, `research.md`, `data-model.md`, `contracts/`

## Execution Flow (summary)
- TDD-first: contract tests -> integration tests -> implementation
- Numbered tasks (T001...) with [P] when safe to run in parallel (different files)

---

## Phase 1: Setup
- T001 Initialize backend Python project structure and virtual environment
  - Files: `pyproject.toml`, `src/backend/`
- T002 Create `Dockerfile` for backend and `docker-compose.yml` at repo root
  - Files: `backend/Dockerfile`, `docker-compose.yml`
- T003 [P] Add VS Code devcontainer config
  - Files: `.devcontainer/devcontainer.json`, `.devcontainer/docker-compose.yml`
- T004 [P] Add CI skeleton with linting (flake8/ruff) and pytest
  - Files: `.github/workflows/ci.yml`

> NOTE: Per repo inspection, T001 - T003 are completed on this branch. `data-model.md` and `contracts/` are not present in the feature directory; tasks that depend on those artifacts are deferred until those documents are added.

---

## Phase 2: Tests First (TDD) — MUST create failing tests before implementation

Contract tests (from `contracts/openapi.yaml`) — put in `tests/contract/`
- T005 [P] Contract test: `tests/contract/test_projects_list.py` for GET /api/v1/projects (expect 200, JSON array)
- T006 [P] Contract test: `tests/contract/test_projects_create.py` for POST /api/v1/projects (expect 201 and resource schema)
- T007 [P] Contract test: `tests/contract/test_models_upload.py` for POST /api/v1/projects/{project_id}/models (expect 201)
- T008 [P] Contract test: `tests/contract/test_model_get.py` for GET /api/v1/models/{model_id}
- T009 [P] Contract test: `tests/contract/test_keys_create_list_revoke.py` for POST/GET/DELETE /api/v1/keys

--

### Immediate executable tasks (no contracts/data-model required)

- T005 [P] Add basic health endpoint test to `src/backend/test_main.py` (fastapi TestClient) — ensure test exists and fails if endpoint missing.
- T006 [P] Add DB connectivity smoke test to `src/backend/test_main.py` that reads `DATABASE_URL` and:
  - For `sqlite` URLs: attempts a simple `SELECT 1`.
  - For network DBs: attempts to open a TCP connection to host:port.
  - Test should `pytest.skip` if `DATABASE_URL` is unset or cannot be parsed.
- T007 Add application factory and health endpoint (if missing) in `src/backend/main.py` so `T005` can pass.

These tasks let you run tests locally in devcontainer without generated contracts. Mark T005 and T006 [P] as parallel-safe since they touch `src/backend/test_main.py` and will be independent if implemented in separate files or guarded by different names.

Integration tests — put in `tests/integration/` and run against docker-compose test env
- T010 [P] Integration test: user registration & login `tests/integration/test_auth_flow.py`
- T011 [P] Integration test: project lifecycle (create, get, update, delete) `tests/integration/test_project_lifecycle.py`
- T012 [P] Integration test: model upload and metadata persistence `tests/integration/test_model_upload.py`
- T013 [P] Integration test: API key scoped access `tests/integration/test_api_key_scopes.py`

Unit tests (supporting)
- T014 [P] Unit tests: validation logic for project/model metadata `tests/unit/test_validation.py`

---

## Phase 3: Core Implementation (only after tests fail)

Models & DB
- T015 [P] Implement User SQLAlchemy model and Alembic migration
  - Files: `backend/src/models/user.py`, `backend/migrations/versions/*`
- T016 [P] Implement Project SQLAlchemy model with JSONB metadata and Alembic migration
  - Files: `backend/src/models/project.py`, migration
- T017 [P] Implement Model (3D file) SQLAlchemy model and migration
  - Files: `backend/src/models/model.py`, migration
- T018 [P] Implement APIKey SQLAlchemy model and migration

Services & Business Logic
- T019 [P] Implement UserService CRUD in `backend/src/services/user_service.py`
- T020 [P] Implement ProjectService CRUD in `backend/src/services/project_service.py`
- T021 [P] Implement ModelService for file handling and metadata in `backend/src/services/model_service.py`

API Endpoints
- T022 POST `/api/v1/projects` implementation (route + handler) -> `backend/src/api/projects.py`
- T023 GET `/api/v1/projects` implementation -> `backend/src/api/projects.py`
- T024 POST `/api/v1/projects/{project_id}/models` implementation (file upload handler) -> `backend/src/api/models.py`
- T025 GET `/api/v1/models/{model_id}` implementation -> `backend/src/api/models.py`
- T026 Keys endpoints: create/list/revoke -> `backend/src/api/keys.py`

Auth & Security
- T027 [P] Implement authentication middleware (session + API key header) -> `backend/src/middleware/auth.py`
- T028 [P] Integrate OAuth provider support (GitHub, Google) using Authlib -> `backend/src/auth/oauth.py`

Storage & Media
- T029 [P] Implement media storage adapter (local filesystem), configuration, and tests -> `backend/src/storage/local.py`

Observability & Logging
- T030 [P] Add structured JSON logging config and file rotation -> `backend/src/logging.py`

---

## Phase 4: Integration & Polish

- T031 Connect services to DB and wire DI in application factory -> `backend/src/app.py`
- T032 Add input validation schemas (Pydantic) for request/response -> `backend/src/schemas/`
- T033 Add frontend Flask/Jinja2 simple UI pages for projects list and project detail -> `frontend/` or `backend/src/frontend/`
- T034 [P] Add thumbnail generation/render fallback logic for missing images -> `backend/src/services/thumbnail.py`
- T035 [P] Add log rotation and retention script in `scripts/` and config -> `scripts/log-rotate.sh`

---

## Phase 5: Docs, Tests, and Release

- T036 Update README with Quickstart and Devcontainer steps -> `README.md`
- T037 Add CHANGELOG entry and bump version (semver) -> `CHANGELOG.md`, bump in `pyproject.toml`
- T038 Run full test suite and ensure green in CI -> `.github/workflows/ci.yml`

---

## Ordering & Dependencies (high level)
- Contract tests (T005-T009) and integration tests (T010-T013) must exist and fail before core implementation tasks (T015-T026).
- Model migrations (T016-T018) must be created before wiring services to DB (T031).
- Auth (T027) required before API key tests (T013) pass.

---

If you'd like, I can now scaffold the repository files for the highest-priority tasks (T001-T006) and create failing contract tests (T005-T009) so you have a runnable TDD baseline. Which set do you want me to start with?
