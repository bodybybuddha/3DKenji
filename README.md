# 3DKenji

Self-hosted knowledge keeper for 3D printing projects. Manage, organize, and track your 3D models and printing projects with a modern REST API.

**Status**: MVP Complete ✅ | Production Ready | All Core Features Implemented

## Features

### 🔐 User Management
- User registration with email validation
- Secure password authentication with JWT tokens
- Password change functionality
- 24-hour session tokens with bearer authentication

### 📁 Project Management
- Create, read, update, and delete printing projects
- Organize models by project
- **Hybrid storage**: Database for identity/metadata, filesystem for artifacts and docs
- ProjectInfo.md and PrintHistory.md with YAML-like frontmatter for structured metadata
- Full ownership and permission validation
- Filesystem directories backed by persistent STORAGE_ROOT volume

### 🎨 3D Model Management
- Upload 3D model files (.stl, .3mf, .obj, .gcode)
- Automatic file validation (type and size constraints, max 10MB)
- List and retrieve model metadata
- Store files in pluggable storage backends
- Support for custom metadata and tags

### 🔑 API Keys
- Generate secure API keys for programmatic access
- Create, list, and revoke keys per user
- Scoped permissions system
- Keys shown only once at creation

### 🏥 Health Monitoring
- Full system status health checks
- Kubernetes readiness and liveness probes
- Component health reporting (storage, database)
- Built for orchestrated deployments

### 📊 Observability
- Structured JSON logging with timestamps
- Log rotation and retention management
- Request tracking with user and request IDs
- Performance metrics and duration tracking

## Quick Start

### Option 1: Docker Compose (Recommended)
```bash
git clone https://github.com/yourusername/3dkenji.git
cd 3dkenji
docker-compose up
```

The API will be available at `http://localhost:8000` with docs at `http://localhost:8000/docs`.

### Option 2: Local Development
```bash
# Clone and enter directory
git clone https://github.com/yourusername/3dkenji.git
cd 3dkenji

# Install dependencies (creates virtual environment)
make install

# Run development server
make dev
```

Server runs at `http://localhost:8000`.

### Option 3: Devcontainer
Open in VS Code with devcontainer extension. It automatically:
- Creates Python virtual environment
- Installs all dependencies
- Starts PostgreSQL database
- Sets up debugging

## API Usage Examples

### 1. Register a User
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "alice",
    "email": "alice@example.com",
    "password": "SecurePassword123!",
    "display_name": "Alice"
  }'
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 2. Create a Project
```bash
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "Benchy Prints",
    "description": "Benchmarking calibration prints"
  }'
```

### 3. Upload a 3D Model
```bash
curl -X POST http://localhost:8000/api/v1/projects/1/models \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@benchy.stl" \
  -F "tags=calibration,test"
```

### 4. List Your Projects
```bash
curl -X GET http://localhost:8000/api/v1/projects \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Create an API Key
```bash
curl -X POST http://localhost:8000/api/v1/keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "CI/CD Deploy"}'
```

Get response with secret (shown once only):
```json
{
  "id": "key_abc123",
  "name": "CI/CD Deploy",
  "secret": "sk_live_abc123xyz789..."
}
```

## API Reference

### Authentication
- `POST /api/v1/auth/register` – Create account and get JWT token
- `POST /api/v1/auth/login` – Login with credentials
- `POST /api/v1/auth/password-change` – Update password (requires auth)

All protected endpoints require `Authorization: Bearer <token>` header.

### Projects
- `GET /api/v1/projects` – List user's projects (paginated)
  - Query: `skip`, `limit`
- `POST /api/v1/projects` – Create new project
- `GET /api/v1/projects/{id}` – Get project details
- `PATCH /api/v1/projects/{id}` – Update project
- `DELETE /api/v1/projects/{id}` – Delete project (cascades)

### Models
- `POST /api/v1/projects/{project_id}/models` – Upload model file
  - Accepts: `.stl`, `.3mf`, `.obj`, `.gcode`
  - Max size: 10MB
- `GET /api/v1/projects/{project_id}/models` – List project models
- `GET /api/v1/models/{id}` – Get model metadata

### API Keys
- `POST /api/v1/keys` – Generate new API key
- `GET /api/v1/keys` – List user's keys
  - Note: Secrets never returned in list
- `DELETE /api/v1/keys/{id}` – Revoke key

### Health & Status
- `GET /api/v1/health` – Full system health status
- `GET /api/v1/health/ready` – Kubernetes readiness probe
- `GET /api/v1/health/live` – Kubernetes liveness probe
- `GET /docs` – OpenAPI interactive documentation

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/kenji

# Storage
STORAGE_ROOT=/data/storage

# Logging
LOG_DIR=/data/logs
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5

# Security
SECRET_KEY=your-secret-key-for-jwt-signing
```

Project directories are created at:

```text
STORAGE_ROOT/Projects/<category>/<slug>
```

Each project includes:
- **ProjectInfo.md** – Project metadata (frontmatter) and documentation
- **PrintHistory.md** – Print session log with metadata and session records
- **models/, cad_files/, timelapse/, images/** – Artifact directories

For complete details on filesystem layout, frontmatter schemas, and markdown formats, see [docs/project-storage-architecture.md](docs/project-storage-architecture.md).

### Docker Environment
Set variables in `.env` file:
```
DATABASE_URL=postgresql://kenji:kenji@postgres:5432/kenji
STORAGE_ROOT=/data/storage
LOG_DIR=/data/logs
SECRET_KEY=dev-secret-key
```

### VS Code MCP Configuration

This workspace includes MCP server configuration in `.vscode/mcp.json` and auto-start is enabled in `.vscode/settings.json` via `chat.mcp.autostart`.

For the PostgreSQL MCP server, store the connection string in the workspace `.env` file using:

```bash
DATABASE_URL=postgresql://kenji:kenji@db:5432/kenji
```

Notes:
- `.env` is gitignored, so secrets are not committed.
- MCP Postgres reads from `DATABASE_URL` through `envFile` in `.vscode/mcp.json`.
- After changing `.env`, restart the Postgres MCP server from `MCP: List Servers`.

### VS Code Copilot Skills

This repository includes custom workspace skills and they are already installed at `.github/skills/`.

- Skills index: [.github/skills/README.md](.github/skills/README.md)
- Example invocation in chat: `/qa-gate-runner`
- Skills are loaded on demand, not all at once.
- Custom project skills are configured as primary.
- Awesome-derived skills are installed as fallback helpers.

### VS Code Copilot Instructions

Project instructions are stored in `.github/instructions/` (not repository root).

- `.github/instructions/project-context.instructions.md`
- `.github/instructions/fastapi-backend.instructions.md`
- `.github/instructions/database-storage.instructions.md`
- `.github/instructions/testing-quality.instructions.md`

These are split by concern so Copilot can load the most relevant guidance per task/file scope.

## Database Setup

Migrations run automatically on startup. To manually run migrations:

```bash
# Apply all pending migrations
alembic upgrade head

# Create a new migration after schema changes
alembic revision --autogenerate -m "Add new field"
```

Database schema:
- `users` – User accounts and authentication
- `projects` – Project organization
- `models` – 3D model metadata
- `apikeys` – API key storage with hashed secrets

## Plugin System

3DKenji uses a plugin architecture for extensibility:

### Built-in Plugins

**AuthProvider** – PasswordAuthProvider
- Handles password registration and login
- Supports custom implementations (GitHub, Google OAuth)

**StorageBackend** – LocalStorageBackend
- Persists files to local filesystem
- Future: S3, Azure Blob Storage plugins

See [PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) for creating custom plugins.

## Testing

```bash
# Run all tests
make test

# Run specific test file
python -m pytest tests/unit/test_storage_backend.py -v

# Run with coverage
python -m pytest --cov=backend tests/

# Watch for changes and re-run
pytest-watch
```

**Test Coverage**: 52 tests
- Unit tests: Services, storage, core utilities
- Integration tests: API contract tests
- All tests pass ✅

## Development

### Project Structure
```
backend/
├── api/                    # API endpoints
│   ├── auth.py            # Authentication
│   ├── projects.py        # Project management
│   ├── models.py          # Model uploads
│   ├── keys.py            # API key management
│   └── health.py          # Health probes
├── services/              # Business logic
│   ├── user_service.py
│   ├── project_service.py
│   ├── model_service.py
│   └── thumbnail.py
├── plugins/               # Pluggable components
│   ├── auth_password.py
│   └── storage_local.py
├── core/                  # Core utilities
│   ├── auth.py           # JWT utilities
│   ├── plugin_interfaces.py
│   └── plugins.py
├── db/                    # Database layer
│   ├── __init__.py       # Session management
│   └── models/           # SQLAlchemy ORM models
├── logging_config.py      # Structured JSON logging
├── storage.py            # Storage initialization
└── main.py               # FastAPI app factory
```

### Development Commands

```bash
# Install development dependencies
make install

# Start development server with auto-reload
make dev

# Run tests with watch mode
make test-watch

# Format code
make format

# Check linting
make lint
```

### Making Changes

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Make changes following project structure
3. Write tests for new functionality
4. Run test suite: `make test`
5. Commit: `git commit -am "Add feature"`
6. Push: `git push origin feature/my-feature`
7. Open pull request

## Deployment

### Docker
```bash
# Build image
docker build -t 3dkenji:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://... \
  -e STORAGE_ROOT=/data/storage \
  -v storage_data:/data/storage \
  3dkenji:latest
```

### Kubernetes
Health check endpoints are Kubernetes-ready:
```yaml
livenessProbe:
  httpGet:
    path: /api/v1/health/live
    port: 8000
readinessProbe:
  httpGet:
    path: /api/v1/health/ready
    port: 8000
```

### Production Checklist
- [ ] Set strong `SECRET_KEY`
- [ ] Use production PostgreSQL instance
- [ ] Configure persistent storage volume
- [ ] Set up log rotation (use `/workspace/scripts/log-rotate.sh`)
- [ ] Enable HTTPS/TLS
- [ ] Configure CORS for frontend domain
- [ ] Set up monitoring and alerting
- [ ] Regular database backups

## Troubleshooting

### Port already in use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Database connection error
```bash
# Check PostgreSQL is running
docker-compose ps

# Verify DATABASE_URL is correct
echo $DATABASE_URL
```

### Storage permission denied
```bash
# Ensure storage directory is writable
chmod -R 755 /data/storage
```

### Tests failing
```bash
# Clear test database and retry
make test

# Run specific test with verbose output
python -m pytest tests/unit/test_storage_backend.py -vv
```

## Logging

Logs are output as structured JSON:
```json
{
  "timestamp": "2026-02-21T10:30:45.123Z",
  "level": "INFO",
  "logger": "backend.api.projects",
  "message": "Project created",
  "module": "projects",
  "function": "create_project",
  "line_number": 45,
  "user_id": "user_123",
  "request_id": "req_abc123",
  "duration_ms": 142
}
```

Logs are written to:
- **Console**: Real-time output for development
- **File**: `/data/logs/app.log` with rotation (10MB, 5 backups)

## Security

- **Authentication**: JWT bearer tokens with 24-hour expiration
- **Passwords**: Bcrypt hashing with automatic salt
- **Authorization**: Per-user resource ownership validation
- **API Keys**: Hashed storage with identifier prefix
- **File Validation**: Type and size constraints
- **HTTPS**: Recommended for production

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch from `dev`
3. Add tests for new features
4. Ensure all tests pass locally
5. Submit a pull request to `dev`

See [.github/SETUP_GUIDE.md](.github/SETUP_GUIDE.md) for detailed setup instructions.

## Development Workflow

This project follows a **feature → dev → main** workflow with branch protection:

### Branch Structure

```
main (production)    ← Stable releases only, requires approval
  ↑
dev (integration)    ← Active development, requires CI to pass
  ↑
feature branches     ← Individual features/fixes
```

### Creating a New Feature

```bash
# 1. Start from dev branch
git checkout dev
git pull origin dev

# 2. Create feature branch
git checkout -b feature/my-awesome-feature

# 3. Make changes and commit
git add .
git commit -m "Add awesome feature"

# 4. Run tests locally
make test

# 5. Push to remote
git push origin feature/my-awesome-feature

# 6. Create pull request to dev
gh pr create --base dev --head feature/my-awesome-feature
```

### Merging to Dev

- ✅ CI tests must pass
- ✅ All conversations resolved
- ✅ Code reviewed (optional but recommended)
- Merge via GitHub UI
- Delete feature branch after merge

### Creating a Release

```bash
# 1. When dev is ready for production
gh pr create --base main --head dev --title "Release v1.1.0"

# 2. After approval and CI pass, merge to main

# 3. Tag the release
git checkout main
git pull origin main
git tag -a v1.1.0 -m "Release v1.1.0: New features and fixes"
git push origin v1.1.0

# 4. Create GitHub release from tag (optional)
gh release create v1.1.0 --notes "Release notes here"
```

### Branch Protection Rules

- **`main`**: Cannot be deleted, requires 1 approval, requires CI, linear history
- **`dev`**: Cannot be deleted, requires CI, no force push
- **Feature branches**: No restrictions, delete after merge

### PR Labels and Release Tags

Use labels to classify intent and keep release flow predictable:

- `type: docs` for documentation-only updates
- `type: backend` for application code changes
- `type: ci-cd` for workflow/automation changes

Tag strategy for production releases:

- Use semantic version tags (`vMAJOR.MINOR.PATCH`) on `main` only.
- Keep docs-only updates deployable to GitHub Pages without creating production release tags.

Automation notes:

- PR labels are auto-applied by `.github/workflows/labeler.yml` and `.github/labeler.yml`.
- Docs and Pages pipeline runs from `.github/workflows/docs-pages.yml`.
- Code CI skips docs-only changes via path filters in `.github/workflows/ci.yml`.

### Running Tests Locally

```bash
# Run all tests
make test

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_storage_backend.py -v

# Run tests matching pattern
pytest -k "test_user" -v
```

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/

# Type checking (optional)
mypy src/
```

For more details, see [.github/SETUP_GUIDE.md](.github/SETUP_GUIDE.md).

## Status & Roadmap

### ✅ MVP Complete (v1.0.0)
- User authentication with JWT
- Project and model management
- File upload and storage
- API key generation
- Health monitoring
- Structured logging

### 🚀 Future Features
- OAuth integrations (GitHub, Google)
- S3 and cloud storage backends
- 3D model rendering and preview
- WebSocket for real-time updates
- Print job tracking
- Timelapse support
- Mobile app

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: [Online docs](https://3dkenji-docs.example.com)
- **Issues**: [GitHub Issues](https://github.com/yourusername/3dkenji/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/3dkenji/discussions)

---

**Built with ❤️ for the 3D printing community**