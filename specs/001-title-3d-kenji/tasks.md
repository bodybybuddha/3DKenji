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

### 3a: Plugin Framework & Models

Plugin Framework
- T015 [P] Implement PluginManager class for plugin discovery/loading -> `backend/src/core/plugins.py`
  - Load plugins from `backend/plugins/` directory
  - Initialize plugins at startup via `register()` method
  - Health checks for plugin status
- T016 [P] Create plugin base interfaces and ABC definitions -> `backend/src/core/plugin_interfaces.py`
  - KeajiPlugin (base), AuthProvider, MediaProcessor, Viewer, StorageBackend, MetadataHandler

Data Models & DB
- T017 [P] Implement User SQLAlchemy model and Alembic migration
  - Files: `backend/src/models/user.py`, `backend/migrations/versions/*`
- T018 [P] Implement Project SQLAlchemy model with JSONB metadata and Alembic migration
  - Files: `backend/src/models/project.py`, migration
- T019 [P] Implement Model (3D file) SQLAlchemy model and migration
  - Files: `backend/src/models/model.py`, migration
- T020 [P] Implement APIKey SQLAlchemy model and migration

Services & Business Logic
- T021 [P] Implement UserService CRUD in `backend/src/services/user_service.py`
- T022 [P] Implement ProjectService CRUD in `backend/src/services/project_service.py`
- T023 [P] Implement ModelService for file handling and metadata in `backend/src/services/model_service.py`

### 3b: Auth & Security (Plugin-based)

Core Auth Middleware
- T024 [P] Implement core auth middleware (token validation, permission checks, rate limiting) -> `backend/src/middleware/auth.py`
  - Validates session cookies and API key headers
  - Calls AuthProvider plugins to validate tokens
  - Enforces role-based access control (RBAC)
  - Does NOT implement auth strategy (delegated to plugins)

Auth Provider Plugins
- T025 Implement password/username AuthProvider plugin -> `backend/plugins/auth_password.py`
  - Handles user registration, login, password hashing
- T026 Implement GitHub OAuth AuthProvider plugin -> `backend/plugins/auth_github.py`
  - Uses Authlib for OAuth flow
- T027 Implement Google OAuth AuthProvider plugin -> `backend/plugins/auth_google.py`
  - Uses Authlib for OAuth flow
- T028 Add `/api/v1/auth/login` endpoint that delegates to active auth providers -> `backend/src/api/auth.py`
- T029 Add `/api/v1/auth/providers` endpoint to list active auth providers (for frontend discovery) -> `backend/src/api/auth.py`

### 3c: Storage (Plugin-based)

Storage Plugin Framework
- T030 [P] Implement StorageBackend plugin interface -> `backend/src/core/plugin_interfaces.py` (update T016)
- T031 [P] Implement local filesystem storage plugin -> `backend/plugins/storage_local.py`
  - File persistence, directory management, access control
- T032 [P] Implement S3-compatible storage plugin skeleton -> `backend/plugins/storage_s3_compat.py` (optional for MVP)

Storage Configuration & Routes
- T033 [P] Add storage adapter load/initialization in app factory
  - Load configured storage backend via PluginManager
  - Expose storage to services

### 3d: API Endpoints

Projects & Models
- T034 POST `/api/v1/projects` implementation -> `backend/src/api/projects.py`
- T035 GET `/api/v1/projects` implementation -> `backend/src/api/projects.py`
- T036 POST `/api/v1/projects/{project_id}/models` implementation (file upload) -> `backend/src/api/models.py`
- T037 GET `/api/v1/models/{model_id}` implementation -> `backend/src/api/models.py`

API Keys
- T038 Keys endpoints: create/list/revoke -> `backend/src/api/keys.py`

### 3e: Observability & Logging
- T039 [P] Add structured JSON logging config and file rotation -> `backend/src/logging.py`
- T040 [P] Add plugin health check endpoint -> `backend/src/api/health.py`

---

## Phase 4: Integration & Polish

- T041 [P] Wire DI (dependency injection) in application factory -> `backend/src/app.py`
  - Load PluginManager, initialize auth providers
  - Register storage backend
  - Wire services to DB
- T042 [P] Add input validation schemas (Pydantic) for request/response -> `backend/src/schemas/`
- T043 [P] Add thumbnail generation/render fallback logic for missing images -> `backend/src/services/thumbnail.py`
- T044 [P] Add log rotation and retention script in `scripts/` and config -> `scripts/log-rotate.sh`
- T045 Add frontend Flask/Jinja2 simple UI pages for projects list and project detail -> `backend/src/frontend/` or `frontend/`
  - Frontend discovers auth providers via `GET /api/v1/auth/providers`
  - Frontend dynamically renders login buttons for available providers
  - Handles OAuth callback for multi-provider login

---

## Phase 5: Docs, Tests, and Release

- T046 Update README with Quickstart and Devcontainer steps -> `README.md`
- T047 Create `/docs` folder structure with Jekyll config for GitHub Pages -> `docs/` (aligns with 002-plugin-architecture)
  - Getting started guide, API reference, plugin development guide
- T048 Add developer guide for plugin creation (auth, storage, viewers) -> `docs/plugins/building-plugins.md`
- T049 Add CHANGELOG entry and bump version (semver) -> `CHANGELOG.md`, bump in `pyproject.toml`
- T050 Run full test suite and ensure green in CI -> `.github/workflows/ci.yml`

---

## Ordering & Dependencies (high level)
- Contract tests (T005-T009) and integration tests (T010-T013) must exist and fail before core implementation tasks (T015+).
- PluginManager (T015) and plugin interfaces (T016) are foundational; most tasks depend on these.
- Data models (T017-T020) must be created before services (T021-T023) and wiring (T041).
- Core auth middleware (T024) must exist before auth provider plugins (T025-T029) can be integrated.
- Storage plugin (T031) required before ModelService (T023) can persist files.
- All endpoints (T034-T038) depend on services (T021-T023) and auth middleware (T024).
- Frontend (T045) requires `/api/v1/auth/providers` endpoint (T029) to discover login options.

---

If you'd like, I can now scaffold the repository files for the highest-priority tasks and create failing contract tests so you have a runnable TDD baseline.

---

## Alignment with 002-plugin-architecture

These tasks are now aligned with the plugin architecture defined in `specs/002-plugin-architecture/spec.md`:
- **Auth is plugin-based**: Core middleware validates; AuthProvider plugins implement strategies (password, GitHub, Google).
- **Storage is plugin-based**: Core uses StorageBackend plugins (local, S3, etc.).
- **Extensibility built-in**: Media processors, viewers, and custom metadata handlers can be added as plugins without core changes.
- **Frontend discovery**: Frontend queries `/api/v1/auth/providers` to dynamically show available login options.
- **Documentation**: `/docs` folder with plugin development guide, complementing 002's strategy.
