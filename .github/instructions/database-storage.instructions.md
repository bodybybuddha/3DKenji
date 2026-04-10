---
description: "Use when changing SQLAlchemy models, Alembic migrations, or filesystem-frontmatter storage behavior in 3DKenji."
name: "Database and Storage Safety"
applyTo: ["migrations/**/*.py", "src/backend/db/**/*.py", "src/backend/storage.py", "src/backend/services/**/*.py"]
---
# Database and Storage Safety

- Prefer additive, backward-compatible schema changes first.
- Ensure each migration has a viable downgrade unless explicitly irreversible by design.
- Keep SQLAlchemy model definitions aligned with Alembic migrations.
- Preserve existing project directory compatibility when changing path/frontmatter behavior.

## Change Checklist

1. Validate migration safety and rollback expectations.
2. Verify DB and filesystem behavior together for lifecycle changes.
3. Add tests for migration-sensitive or path/frontmatter-sensitive behavior.
4. Call out any data or compatibility risk in change summaries.
