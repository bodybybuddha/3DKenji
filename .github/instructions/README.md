# Copilot Instructions Index

This folder contains workspace instruction files used by GitHub Copilot.

## Purpose

Instruction files in this directory provide focused, domain-specific guidance so the agent can load relevant rules based on task intent and file scope.

## Files

1. `project-context.instructions.md`
   - Scope: repository-wide context and architecture guidance.
   - Trigger: on-demand when project-level context is needed.

2. `fastapi-backend.instructions.md`
   - Scope: FastAPI backend code standards and change checklist.
   - Auto-attach: `src/backend/**/*.py`

3. `database-storage.instructions.md`
   - Scope: SQLAlchemy, Alembic, and filesystem/frontmatter safety guidance.
   - Auto-attach: migrations and storage-related backend files.

4. `testing-quality.instructions.md`
   - Scope: test strategy and quality gate expectations.
   - Auto-attach: `tests/**/*.py`

5. `dev-cycle.instructions.md`
   - Scope: commit, PR, merge, branch-protection, and tag/release workflow guidance.
   - Trigger: on-demand when repository delivery workflow or GitHub operations are involved.

## Notes

- Keep one concern per instruction file.
- Prefer concise, actionable rules over long prose.
- Use `applyTo` only where deterministic file-based attachment is beneficial.
