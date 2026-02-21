# Research: 3D Kenji Core

Decision: Use FastAPI for API-first development; retain Flask/Jinja2 for initial UI convenience pages.

Rationale: FastAPI provides automatic OpenAPI generation and async support. Flask is familiar and useful for small server-rendered pages during early UI iterations.

Alternatives considered:
- Django REST Framework — heavier, more opinionated; rejected for a smaller, modular project.
- Pure Flask API — lacks first-class OpenAPI tooling compared to FastAPI.

Media storage decision: default to local file storage under `/data/media` with a storage abstraction to allow S3-compatible backends.

Auth decision: username/password + OAuth via Authlib; scoped API keys stored hashed in DB. Consider using jwks endpoint if JWTs used.

File types: initial whitelist [.stl, .3mf, .obj, .gcode]. Max file size default 100MB; configurable.

Logging: structured JSON logs to file with rotation (logrotate or Python logging.handlers.RotatingFileHandler). Provide env-configurable sinks.

DB migrations: Alembic with SQLAlchemy models. Use JSONB columns for flexible metadata.

Dev environment: VS Code devcontainer + docker-compose to bring up backend, frontend, and Postgres. Use lightweight base images (python:3.11-slim).

Artifacts created by /plan:
- `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/data-model.md`
- `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/contracts/openapi.yaml`
- `/Users/jtaylor/Documents/projects/3DKenji/specs/001-title-3d-kenji/quickstart.md`
