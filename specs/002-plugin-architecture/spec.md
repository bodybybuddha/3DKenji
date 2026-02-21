# Plugin Architecture & Documentation Strategy

**Created**: 2026-02-21  
**Status**: Planning  
**Related Feature**: 3D Kenji Core (001-title-3d-kenji)

## Overview

This document outlines the plugin architecture necessary to support extensibility (e.g., timelapse capture companions, file format viewers) and the documentation strategy using GitHub Pages.

---

## 1. Plugin Architecture Requirements

### 1.1 Goals
- Allow third-party and internal extensions to register handlers for:
  - **Media processors** (timelapse creation from photo sequences)
  - **File viewers** (3D model renderers, document previewers)
  - **Import/export pipelines** (external service integrations)
  - **Custom metadata handlers** (domain-specific project data)
- Minimal coupling: plugins should run independently; core should not break when plugins fail
- API-first discovery: plugins register capabilities via a plugin registry endpoint

### 1.2 Core Plugin Concepts

#### Plugin Registry
- Plugins register themselves at application startup
- Core maintains a registry of:
  - Plugin name, version, author
  - Capabilities (viewer types, processors, formatters)
  - Webhook endpoints or file paths plugins expose
  - Authorization scopes required

#### Plugin Types
1. **Media Processor** – accepts media files, project/model context, and returns processed output
   - Example: "Extract frames from video → render timelapse → store in project"
   - Triggered by webhook POST or scheduled task
   
2. **Viewer/Renderer** – accepts model/media resource, returns HTML/embed or asset URL
   - Example: "3D model → WebGL/Three.js preview"
   - Called when frontend requests resource representation
   
3. **Storage Backend** – abstraction for persisting media/models
   - Example: local filesystem, S3/MinIO, Azure Blob Storage
   - Swappable via configuration
   
4. **Auth Provider** – pluggable authentication strategy (username/password, OAuth, LDAP, SAML)
   - Example: "GitHub OAuth" → user lookup/creation → JWT/session token
   - Integrated with core permission middleware; core validates tokens
   - Multiple providers can be active simultaneously; frontend chooses which to initiate
   
5. **Metadata Handler** – custom schema validators, enrichment pipelines
   - Example: "Receive GCODE settings → validate against known printer profiles"

#### Plugin Interface (Python)
```python
from abc import ABC, abstractmethod

class KeajiPlugin(ABC):
    """Base interface for all plugins."""
    
    name: str  # e.g., "timelapse-processor"
    version: str
    author: str
    capabilities: list[str]  # e.g., ["media-processor"]
    
    @abstractmethod
    def register(self, app: FastAPI, config: dict) -> None:
        """Called at startup. Plugin registers routes/handlers."""
        pass
    
    @abstractmethod
    def health_check(self) -> dict:
        """Return plugin status for observability."""
        pass

class MediaProcessor(KeajiPlugin):
    """Process media (timelapse, resizing, transcoding)."""
    
    @abstractmethod
    async def process(
        self, 
        source_path: str, 
        project_id: str, 
        model_id: str | None,
        metadata: dict
    ) -> ProcessResult:
        """Process source file and return result metadata + output path."""
        pass

class Viewer(KeajiPlugin):
    """Render or preview a resource."""
    
    @abstractmethod
    async def render(
        self, 
        resource_id: str, 
        resource_type: str,  # "model", "media", "note"
        context: dict
    ) -> ViewerResponse:
        """Return HTML, asset URL, or embed code."""
        pass

class AuthProvider(KeajiPlugin):
    """Pluggable authentication strategy."""
    
    auth_type: str  # "password", "github", "google", "ldap", "saml"
    
    @abstractmethod
    async def authenticate(
        self, 
        credentials: dict
    ) -> AuthResult:
        """
        Authenticate user and return identity.
        credentials: provider-specific (e.g., {"username", "password"} or {"code", "state"}).
        Returns: AuthResult with user identity, email, display_name, and optional scopes.
        """
        pass
    
    @abstractmethod
    async def get_login_url(self, state: str, redirect_uri: str) -> str | None:
        """
        For interactive flows (OAuth): return login URL.
        For simple auth (password): return None.
        """
        pass
    
    @abstractmethod
    async def validate_token(self, token: str) -> UserIdentity | None:
        """
        Validate an issued token/session and return user identity.
        Return None if invalid or expired.
        """
        pass
```

#### Plugin Lifecycle
1. **Discovery** – plugins packaged in `backend/plugins/` or loaded via external registry
2. **Initialization** – `register()` called; plugin installs routes/middleware
3. **Runtime** – plugin handles requests; logs via standard logging
4. **Shutdown** – cleanup (close DB connections, flush caches)

### 1.3 Example: Timelapse Capture Plugin

**Scenario**: External timelapse companion app (e.g., Raspberry Pi camera) uploads photos and metadata JSON to a shared directory that 3DKenji can access.

**Workflow**:
1. Companion app uploads frames to `/data/timelapse/{project_name}/` and `metadata.json`
2. Companion calls `POST /api/v1/projects/{project_id}/timelapse/process` with metadata
3. Plugin webhook handler:
   - Validates frames exist and metadata integrity
   - Calls FFmpeg (or configurable encoder) to produce MP4/WebM
   - Stores output in `/data/media/{project_id}/` and updates model record
   - Returns 200 with video URL
4. Frontend displays timelapse in model viewer

**Implementation**:
- Plugin file: `backend/plugins/timelapse_processor.py`
- Entrypoint in `pyproject.toml`: `[project.entry-points."3dkenji.plugins"]`
- Configuration: environment variables or `config.yaml`

### 1.4 File Viewer Plugin Pattern

**Example**: 3D model viewer for .stl/.3mf files.

**Workflow**:
1. Frontend requests `GET /api/v1/models/{id}/viewer?format=webgl`
2. Plugin routes to viewer handler
3. Viewer returns HTML with embedded Three.js + model data URL
4. Frontend renders or uses iframe

**Implementation**:
- Plugin file: `backend/plugins/viewers/` directory
- Each viewer implements `Viewer` interface
- Core model API exposes `viewer_urls` in response, keyed by format

### 1.5 Plugin Isolation & Failures

- **Optional plugins** – if a plugin fails to load, log warning; continue startup
- **Error handling** – plugin failures do not crash core; return 503 or fallback response
- **Telemetry** – plugins log via standard Python logging; core collects metrics
- **Permissions** – plugins declare required scopes; verify before calling sensitive APIs

### 1.6 Auth Provider Integration

Core Auth Middleware remains in core:
- Session validation (cookie checks, JWT verification)
- Permission enforcement (role-based access control)
- Rate limiting, revoked key checks

Auth Providers plug in at **authentication entry points**:
- Login endpoint: `POST /api/v1/auth/login` – delegates to active provider
- OAuth callback: `GET /api/v1/auth/callback` – provider validates OAuth response
- Token validation: core middleware calls provider's `validate_token()` for each request

**Example flow (GitHub OAuth)**:
1. Frontend requests login URL from `POST /api/v1/auth/providers` (lists active providers)
2. Core calls `GitHubAuthProvider.get_login_url()` → returns `https://github.com/login/oauth/authorize?...`
3. User authorizes on GitHub, redirected to `GET /api/v1/auth/callback?code=...&state=...`
4. Core calls `GitHubAuthProvider.authenticate(code)` → returns user identity
5. Core creates session token, returns to frontend
6. Frontend stores token; subsequent requests include token in header
7. Core middleware calls `GitHubAuthProvider.validate_token(token)` for each request

**Benefits**:
- Swap auth providers by configuration change + plugin load
- Multiple providers active simultaneously (user chooses at login)
- Core security logic unchanged; only auth strategy swapped
- Plugins cannot bypass permission checks or session validation

---

## 2. Documentation Strategy (GitHub Pages)

### 2.1 Documentation Root
- Location: `/docs` directory in repository
- Static site generator: Jekyll (GitHub Pages native) or Hugo (faster)
- Hosted at: `https://github.com/bodybybuddha/3DKenji` (Pages > repo root)

### 2.2 Documentation Structure

```
docs/
├── index.md                          # Homepage
├── _config.yml                       # Jekyll config (theme, title, etc.)
├── assets/
│   ├── images/                       # Screenshots, diagrams
│   └── css/
├── getting-started/
│   ├── quickstart.md                 # 5-minute setup via Docker/devcontainer
│   ├── installation.md               # Detailed install & config
│   └── docker-compose-example.md     # Full development environment
├── guides/
│   ├── projects-and-models.md        # User guide
│   ├── api-keys.md                   # API authentication & scopes
│   ├── sharing-and-permissions.md    # Collaboration model
│   └── oauth-setup.md                # GitHub/Google OAuth config
├── api/
│   ├── overview.md                   # API introduction
│   ├── authentication.md             # Auth methods
│   ├── projects.md                   # Project endpoints
│   ├── models.md                     # Model endpoints
│   ├── media.md                      # Media endpoints
│   └── openapi.yaml                  # Link to live spec (or embedded Swagger UI)
├── plugins/
│   ├── overview.md                   # Plugin architecture intro
│   ├── building-plugins.md           # Plugin development guide
│   ├── examples/
│   │   ├── timelapse-processor.md    # Walkthrough of timelapse plugin
│   │   └── custom-viewer.md          # Custom file viewer example
│   └── plugin-registry.md            # Discovering third-party plugins
├── deployment/
│   ├── kubernetes.md                 # K8s deployment
│   ├── systemd.md                    # systemd service
│   ├── environment-variables.md      # Config reference
│   └── database-migrations.md        # Schema upgrade guide
├── contributing/
│   ├── contributing.md               # Contribution guidelines
│   ├── architecture.md               # Code organization, design patterns
│   ├── testing.md                    # Running tests, TDD workflow
│   └── git-workflow.md               # Branching, commit messages, PRs
└── faq.md                            # Frequently asked questions
```

### 2.3 Key Documentation Artifacts

1. **API Reference** – auto-generated from OpenAPI (or manually maintained Swagger UI embed)
2. **Plugin Development Guide** – walkthrough with code samples
3. **Deployment Guides** – Docker, systemd, Kubernetes examples
4. **Architecture Overview** – high-level design diagrams, data flow
5. **FAQ & Troubleshooting** – common issues, debugging tips

### 2.4 Maintenance & Automation

- Docs are versioned with releases (use Git tags for doc branches if needed)
- CI workflow builds docs on every push; preview available for PRs
- Markdown linter enforces style consistency
- Link checker ensures no broken references

---

## 3. Integration with Core

### 3.1 Plugin Discovery & Loading

Core will provide:
```python
# backend/core/plugins.py
class PluginManager:
    def load_plugins(self, plugins_dir: str) -> None:
        """Discover and initialize all plugins."""
        
    def get_processor(self, media_type: str) -> MediaProcessor | None:
        """Retrieve processor for media type."""
        
    def get_viewer(self, resource_type: str) -> Viewer | None:
        """Retrieve viewer plugin."""
        
    def register_webhook(self, name: str, handler: callable) -> None:
        """Plugins call to register event handlers."""
```

### 3.2 Plugin Entrypoints

In `pyproject.toml`:
```toml
[project.entry-points."3dkenji.plugins"]
timelapse = "plugins.timelapse_processor:TimelapsePlugin"
viewer-3d = "plugins.viewers.model_viewer:ModelViewerPlugin"
```

### 3.3 Plugin Configuration

Per-plugin config in environment or `config/plugins.yaml`:
```yaml
plugins:
  auth_providers:
    - type: password
      enabled: true
    - type: github
      enabled: true
      client_id: ${GITHUB_CLIENT_ID}
      client_secret: ${GITHUB_CLIENT_SECRET}
    - type: google
      enabled: true
      client_id: ${GOOGLE_CLIENT_ID}
      client_secret: ${GOOGLE_CLIENT_SECRET}
  timelapse:
    enabled: true
    ffmpeg_path: /usr/bin/ffmpeg
    max_frames: 3600
  viewers:
    enabled: true
    formats: [webgl, image]
  storage:
    backend: local  # or "s3"
    local_path: /data/media
```

---

## 4. Next Steps

1. **Design OpenAPI extensions** – add `x-plugin-id` fields to endpoints that plugins may handle
2. **Create plugin template** – scaffold for developers: `scripts/create-plugin.sh`
3. **Implement PluginManager** – core class in `backend/core/plugins.py`
4. **Set up GitHub Pages** – configure Jekyll, create initial docs site
5. **Write plugin examples** – timelapse processor, 3D model viewer as reference implementations
6. **Documentation generation** – auto-generate plugin registry from entry points

---

## 5. Success Criteria

- [ ] Plugin interface documented and implemented
- [ ] AuthProvider interface created with password and OAuth examples (GitHub, Google)
- [ ] Example plugins (timelapse processor, 3D model viewer, auth providers) created and tested
- [ ] Plugin loading/initialization working without breaking core
- [ ] Auth middleware validates tokens via provider plugins without blocking core startup
- [ ] Multiple auth providers can be active simultaneously; frontend allows user to choose
- [ ] GitHub Pages site live with getting-started guide and API docs
- [ ] Plugin development guide complete with auth provider code examples
- [ ] Plugin registry endpoint available (/api/v1/auth/providers for login options)

