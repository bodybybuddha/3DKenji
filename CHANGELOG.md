# Changelog

All notable changes to 3DKenji are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ✨ Added - Project File Editor and Markdown Viewer

- Added a dedicated text-file editor window launched from Project Files actions for editable formats (`.md`, `.txt`, `.rtf`, and related text/config/code files).
- Added save support for editable files through secure project file content APIs, including keyboard shortcut support (`Ctrl/Cmd+S`) in the editor.
- Added live markdown preview support in the editor via backend markdown render endpoint.
- Added a markdown viewer plugin (`markdown-viewer`) so markdown files render as formatted content in the Project Files preview pane.
- Added an RTF viewer plugin (`rtf-viewer`) so `.rtf` files render in the Project Files preview pane.
- Added rich-text editor mode for `.rtf` files with inline formatting controls and direct save workflow.

### ✨ Added - Project Files New File Flow

- Added a `New File` action in Project Files toolbar to create files directly in the current directory.
- Added backend endpoint `POST /api/v1/projects/{project_id}/files/create` with supported type templates (`md`, `txt`, `rtf`, `json`, `yaml`, `csv`, `log`, `py`, `sql`, `html`).
- Added duplicate-name protection and extension/type validation for created files.

### 🔧 Changed - Project Files Table Actions

- Reworked file table actions so editable files show `Edit` and `View`, while non-editable files retain `Save` download action.
- Removed the Type column and emphasized file/folder type icons in the Name column; retained Size for quick scanning.
- Moved viewer-hook detail messaging into a compact hover info icon to reduce preview panel clutter.

### 🔧 Fixed - Project Files Browser UX and Path Consistency

- Improved Project Files table header contrast so column labels and sort arrows remain legible across theme backgrounds.
- Moved file preview into the same Project Files card with a side-by-side layout for faster browsing and preview workflows.
- Fixed project filesystem root default mismatch so file browser listings align with storage backend uploads in local/dev environments.

### ⚙️ Changed - Developer MCP Bootstrap

- VS Code MCP auto-start now provisions GitHub, Postgres, Playwright, and Chrome DevTools servers from workspace config.
- Postgres MCP now reads from `MCP_POSTGRES_URL` (plain `postgres://` or `postgresql://`) to avoid SQLAlchemy driver URL incompatibilities.
- Added `scripts/bootstrap-mcp.sh` and `make mcp-bootstrap` for one-command MCP cache warming and Playwright Chromium setup.
- Devcontainer post-create now runs MCP bootstrap automatically so frontend browser testing tools are ready after container creation.
- Added `.env.example` and a VS Code task (`Bootstrap MCP prerequisites`) to simplify setup for new contributors.

### ✨ Added - Filesystem Architecture & Archive Feature

#### Filesystem-Backed Projects
- Project directories created alongside database records in `STORAGE_ROOT/Projects/<category>/<slug>`
- ProjectInfo.md with frontmatter (project metadata) and markdown body (documentation)
- PrintHistory.md with frontmatter (file-level metadata) and session entries
- Configurable STORAGE_ROOT environment variable for persistent volume mapping
- Default subdirectories: models/, cad_files/, timelapse/, images/

#### Frontmatter Support
- YAML-like frontmatter parser (no external dependencies)
- ProjectInfo.md frontmatter schema: title, summary, tags, designer, source_url, license, status
- PrintHistory.md frontmatter schema: project, created_date, last_print_date, total_sessions, printer_model, notes
- Backward-compatible frontmatter normalization for existing files
- Frontmatter automatically excluded from HTML rendering

#### Archive Feature
- **Deletion Policy**: Configurable per-project behavior (`archive` default, `hard_delete` option)
- **Archive Behavior**: Move project to archive category instead of permanent deletion
- **Hard Delete Behavior**: Permanent removal for explicit data purging
- **Database Migration**: schema v005 adds deletion_policy field
- **Backward Compatible**: Existing projects default to archive behavior

### 🧪 Testing
- 3 new tests for archive functionality (archive policy, hard_delete policy, default behavior)
- Updated legacy delete tests to reflect new archive-default behavior
- All 60+ project-related tests passing

### 📚 Documentation
- docs/project-storage-architecture.md: Complete hybrid DB+filesystem model explanation
- docs/configuration.md: Frontmatter support explanation and STORAGE_ROOT guidance  
- README.md: Highlights hybrid storage model and frontmatter for structured metadata
- Migration story for backfiller script to upgrade existing projects
- Admin panel integration deferred to next branch

### 🔧 Internal
- ProjectDTO updated with deletion_policy field
- Alembic migration 005 for deletion_policy column
- backend/services/project_service.py: _archive_project() and _hard_delete_project() methods
- ProjectService.delete_project() delegates to policy-specific handlers

---

## [1.1.0] - 2026-02-22

### ✨ Added - QA Infrastructure

#### Testing Framework
- **E2E Testing**: Playwright-based browser automation with 27+ test scenarios
- **Validation Testing**: 75+ tests covering XSS, SQL injection, boundary conditions
- **Test Utilities**: Factory pattern for test data, shared fixtures, database isolation
- **Test Coverage**: 132+ tests total across all layers (unit, integration, validation, E2E)

#### CI/CD Pipeline
- GitHub Actions workflow for automated testing
- Code quality checks on every push/PR
- Branch protection rules configured
- E2E tests run locally only (excluded from CI)

#### Documentation
- QA strategy guide with testing pyramid
- Testing architecture diagrams
- Quick reference command guide
- Validation testing guide with examples
- 200+ item manual QA checklist

#### Developer Tools
- `run-qa-tests.sh` - Comprehensive test runner script
- Pre-commit hook for validation tests
- New Makefile targets: test-fast, test-validation, test-e2e, test-full
- Pytest markers for test categorization

### 🔧 Fixed
- Async storage test event loop conflicts (pytest-asyncio auto mode)
- API key scope enforcement (403 responses for insufficient scopes)
- Health endpoint test compatibility with structured responses

### 📦 Dependencies
- Added: playwright, pytest-playwright, pytest-asyncio, faker

---

## [1.0.0] - 2026-02-21

### ✨ Features (MVP Release)

#### Authentication & Security
- User registration with email validation
- Secure password authentication with bcrypt hashing
- JWT token-based authentication (24-hour expiration)
- Password change functionality
- Bearer token validation on protected endpoints

#### Project Management
- Create, read, update, delete (CRUD) projects
- Organize 3D models by project
- Custom metadata support via JSONB fields
- Full ownership and permission validation
- Cascading delete (deletes all models when project deleted)

#### 3D Model Management
- Upload 3D model files (.stl, .3mf, .obj, .gcode)
- Automatic file validation (type and 10MB size limit)
- List models by project with pagination
- Retrieve model metadata
- Pluggable storage backend (local filesystem implemented)
- Support for tags and custom metadata

#### API Key Management
- Generate secure API keys for programmatic access
- Create, list, and revoke API keys
- Keys shown only once at creation time
- Identifier + hash storage pattern (secure)
- Per-user key management

#### Health Monitoring
- Full system health check endpoint
- Kubernetes readiness probe (`/api/v1/health/ready`)
- Kubernetes liveness probe (`/api/v1/health/live`)
- Component health reporting (storage, database)
- Built-in monitoring for orchestrated deployments

#### Observability
- Structured JSON logging to stdout and file
- Automatic log rotation (10MB files, 5 backups)
- Request tracking with user_id and request_id
- Performance metrics with duration_ms
- Production-ready logging configuration

#### Plugin Architecture
- Extensible plugin system with auto-discovery
- AuthProvider interface (PasswordAuthProvider implemented)
- StorageBackend interface (LocalStorageBackend implemented)
- Ready for: OAuth (GitHub, Google), Cloud storage (S3, Azure)
- Future support for: Media processors, Viewers, Metadata handlers

#### API Features
- 14 REST endpoints across 4 resource types
- OpenAPI/Swagger documentation auto-generated
- Pydantic request/response validation
- Proper HTTP status codes
- Consistent error responses
- Pagination support for list endpoints

#### Database
- SQLAlchemy ORM with Alembic migrations
- PostgreSQL database backend
- User, Project, Model, APIKey tables
- Automatic schema versioning
- Support for complex queries and transactions

#### Development Tools
- Devcontainer configuration for VS Code
- Docker and docker-compose setup
- Make commands for common tasks
- Comprehensive test suite (52 tests)
- Unit, integration, and contract tests

### 📊 Test Coverage

- **Total Tests**: 52 passing
- **Services**: 30 unit tests
- **Storage Backend**: 13 unit tests
- **API Contracts**: 9 integration tests
- **Coverage**: All critical paths covered

### 📚 Documentation

- Comprehensive README with examples
- Getting started guide with quickstart
- Complete API reference documentation
- Configuration guide for all environments
- Plugin development guide with examples
- GitHub Pages ready documentation

### 🏗️ Architecture

- **Framework**: FastAPI with async/await
- **ORM**: SQLAlchemy with Alembic migrations
- **Validation**: Pydantic models
- **Authentication**: JWT with bcrypt
- **Logging**: Structured JSON
- **Testing**: pytest with fixtures
- **Storage**: Pluggable backends

### 🔒 Security Features

- Password validation (8+ characters minimum)
- Bcrypt password hashing with auto salt
- JWT token signing with SECRET_KEY
- API key generation with secure hashing
- Ownership validation on all resources
- Bearer token requirement for protected endpoints
- File type and size validation on uploads
- SQL injection protection via ORM

### 🚀 Deployment Ready

- Docker and docker-compose configurations
- Kubernetes health check endpoints
- Production environment variables
- Log rotation for long-running instances
- Reverse proxy ready (nginx, CloudFlare)
- Database connection pooling ready
- Cloud storage backend support

### Known Limitations

- No rate limiting (add via reverse proxy)
- Single authentication provider (password-based, others available as plugins)
- File download endpoint not implemented (stored files are referenced)
- No real-time WebSocket support
- No built-in 3D rendering (uses plugins/external services)

## Unreleased

### Planned Features

#### Project Lifecycle
- Add configurable project deletion strategy in Admin settings:
	- `archive` (default): move project into archive category/path
	- `hard_delete`: permanently remove project and filesystem artifacts
- Persist deletion strategy in database so behavior is deterministic across restarts
- Keep end-user UI simple by continuing to expose a single "Delete" action
- Introduce archive directory/category conventions under project storage root

### Documentation
- Update docs to describe filesystem-backed project architecture (not only DB metadata)
- Document project directory defaults and storage-root behavior
- Document `ProjectInfo.md` and `PrintHistory.md` structure and expected contents

### Planned Features for v1.1.0

#### Authentication
- GitHub OAuth plugin
- Google OAuth plugin
- SAML/LDAP provider support

#### Storage
- Amazon S3 backend plugin
- Azure Blob Storage plugin
- Google Cloud Storage plugin

#### Media
- 3D model preview/thumbnail generation
- WebSocket support for real-time updates
- Print job tracking
- Timelapse video support

#### Features
- Mobile app (iOS/Android)
- Advanced search and filtering
- Batch operations
- Export/import projects
- Sharing and collaboration

## Upgrade Guide

### Upgrading from Pre-1.0

Version 1.0.0 is the first release and does not have prior versions to upgrade from.

For initial deployment:

1. Clone repository
2. Run `docker-compose up` or `make install && make dev`
3. Create user account via `/api/v1/auth/register`
4. Start creating projects

## Compatibility

- **Python**: 3.10+
- **Database**: PostgreSQL 12+
- **OS**: Linux, macOS, Windows (via Docker/WSL)
- **Docker**: 20.10+
- **Docker Compose**: 1.29+

## Contributors

- Core development team

## License

This project is licensed under the MIT License - see [LICENSE](../LICENSE) file for details.

---

## Release Notes

### What's New in 1.0.0

This is the initial release of 3DKenji with all MVP features:

✅ Full user authentication system  
✅ Project and model management  
✅ File storage with plugin architecture  
✅ API key generation  
✅ Health monitoring for Kubernetes  
✅ Structured JSON logging  
✅ Comprehensive REST API (14 endpoints)  
✅ Production-ready documentation  
✅ 52 passing tests  

The system is fully functional and ready for production deployment for small to medium teams.

### Installation

See [Getting Started](docs/getting-started.md) for installation instructions.

### Known Issues

None reported in initial release. Please file issues on [GitHub](https://github.com/yourusername/3dkenji/issues).

### Future Roadmap

See [Planned Features for v1.1.0](#planned-features-for-v110) above.
