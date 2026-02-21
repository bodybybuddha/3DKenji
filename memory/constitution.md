# 3DKenji Constitution

This constitution records the project's non-negotiable principles, architectural constraints, and governance rules. It is the single source of truth for decisions that affect project structure, developer experience, and public API behavior.

## Purpose

3DKenji is an open source, API-first web application platform that prioritizes flexibility, modularity, and reproducible development environments. The project is Python-based and aims to make it easy for external developers to build alternate frontends and integrations.

## Core Principles

I. Open Source (License)
- The project is released under the MIT license. All contributions must be compatible with MIT. The `LICENSE` file in the repository is authoritative.

II. API-First
- Public behaviour is modeled as machine-readable API contracts (OpenAPI v3 preferred) that are authored before implementation. APIs are the primary integration surface; server-rendered pages (Flask + Jinja2) are allowed for convenience, but every meaningful interaction must also be available via the API.

III. Container-First Development
- All runtime components (backend, frontend, middleware) must be containerized. Development is performed inside devcontainers (VS Code devcontainer definitions preferred; support for other editors documented). CI and release images must be reproducible from the same Dockerfile(s).

IV. Modularity & Extensibility
- Features should be implemented as modular components or libraries with well-defined interfaces so they can be added, modified, disabled, or replaced (plugin-capable architecture). Core behavior is kept minimal; optional features are pluggable.

V. Multi-User and API Key Access
- The system must support multiple users and programmatic access via API keys. A minimal admin interface is required to manage users, API keys, and their scopes/capabilities. Authentication/authorization patterns (JWT, scoped API keys, or OAuth) must be specified in the relevant spec and implemented consistently.

VI. Data Storage
- Postgres is the canonical persistent store. Use JSONB columns for flexible schemas where appropriate. All schema changes must be performed via explicit, versioned migrations.

VII. Observability & Logging
- Structured logging is required. The logging system must be configurable with pluggable sinks (file, stdout, remote collectors). Default local logs are file-based with automatic rotation and archival policies. Instrumentation (metrics, traces) should be added incrementally for critical flows.

VIII. Versioning
- Semantic Versioning (MAJOR.MINOR.PATCH) governs public releases. API compatibility rules, deprecation windows, and migration guides must be documented for breaking changes.

IX. Test-First & Quality Gates
- Prefer spec-driven tests: write contract tests (API + schema) and unit tests before implementation. CI must run linting, type checks (mypy/pyright if used), unit tests, and contract/integration tests. PRs must pass CI and include changelog notes when required.

X. Security & Data Protection
- Follow best practices for secret management, encryption in transit and at rest where applicable, and least-privilege for API keys and admin functions. Sensitive data handling and retention policies must be documented.

## Development Workflow

- Author API contracts (OpenAPI) before implementation. Generate client/server stubs where helpful.
- Implement reusable libraries for core logic; keep HTTP handlers thin adapters that call into well-tested libraries.
- Use migrations for DB changes (e.g., Alembic). Keep migration files in source control.
- Use devcontainers for local development and test running. Document how to start the app and run tests inside the devcontainer.

## Governance

- Amendments to this constitution require a documented proposal and a short migration plan. A ratification entry must be added to the constitution history with version and date.
- PRs that introduce or change public APIs must include: OpenAPI update, migration notes if breaking, tests demonstrating expected behavior, and CI passing.

## Required Repository Artifacts

- `LICENSE` — MIT (already present)
- `memory/constitution.md` — this document (source of truth)
- `templates/spec-template.md` — must include OpenAPI-first guidance and contract test examples
- `templates/plan-template.md` — reference constitution check and API-first decisions
- `templates/tasks-template.md` — include TDD and migration tasks
- `/.devcontainer/` — devcontainer definitions for VS Code
- `Dockerfile` & `docker-compose.*` — reproducible container builds for local development and CI
- `README.md` — quickstart that shows how to run the devcontainer and hit the API
- `scripts/` — developer utilities (migrations, seed, log rotation helper)

## Minimum Technical Decisions (defaults)

- Language: Python 3.11+ (project may opt into newer stable versions)
- Web framework: Flask for server + Jinja2 for optional server-side pages
- Database: PostgreSQL with JSONB for flexible fields
- Auth: scoped API keys + JWT for user sessions (final mechanism to be chosen and documented)
- Logging: structured JSON logs to file + configurable sinks; log rotation and archival enabled by default

## Checklist mapping

When this constitution is amended, update these files/templates as listed in `/memory/constitution_update_checklist.md`:
- `/templates/plan-template.md` — add API-first and devcontainer startup steps
- `/templates/spec-template.md` — require OpenAPI and contract tests
- `/templates/tasks-template.md` — include TDD and migration tasks
- `/.claude/commands/plan.md` and `/.claude/commands/tasks.md` — reflect any changes to planning or task generation
- `/CLAUDE.md` — update runtime development guidance

## Version

**Version**: 0.1.0-draft | **Ratified**: 2025-09-07 | **Last Amended**: 2025-09-07

---

If anything above should be stricter (for example: make TDD mandatory, pick a single auth scheme, or require GraphQL instead of REST), say which items to lock down and I will update the constitution and the checklist patches for the templates.
