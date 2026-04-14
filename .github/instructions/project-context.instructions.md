---
description: "Use when working in the 3DKenji repository and project-level context is needed. Covers architecture, stack, and high-level workflow expectations for FastAPI, PostgreSQL, plugins, and filesystem-backed project metadata."
name: "3DKenji Project Context"
---
# 3DKenji Project Context

- 3DKenji is a FastAPI backend with hybrid storage:
  - PostgreSQL stores identity, ownership, and relational metadata.
  - Filesystem under `STORAGE_ROOT` stores project artifacts and markdown metadata files.
- Key backend code is under `src/backend/`.
- Key tests are under `tests/` with contract, integration, validation, and e2e layers.
- Database evolution uses Alembic migrations under `migrations/`.

## Core Working Rules

- Prefer small, focused changes over broad refactors.
- Preserve existing API contracts unless behavior change is explicitly requested.
- Keep database model changes and migrations synchronized.
- Keep filesystem/frontmatter behavior backward compatible unless migration guidance is included.
- Run relevant tests for changed behavior and report what was validated.

## Branching Strategy

- Use `feature/*` branches for implementation work.
- Use `bugfix/*` branches for bug-specific work when that naming is clearer.
- Use `docs/*` branches for documentation-focused work.
- Use `chore/*` branches for operational or maintenance work.
- Open pull requests from `feature/*`, `bugfix/*`, `docs/*`, or `chore/*` into `dev`.
- Promote `dev` into `main` through controlled release merges.
- **Delete short-lived working branches after a successful merge.** Once a working-branch PR is merged into `dev`, delete the branch both remotely and locally:
  ```bash
  git push origin --delete <branch-name>
  git checkout dev && git pull origin dev
  git branch -d <branch-name>
  ```
- At steady state, only `dev` and `main` should exist.

## Dev Cycle Operating Rules

- Start release-work or feature-work from an up-to-date `dev` branch unless the task is explicitly a `main` release promotion.
- Before opening a PR, check the working tree and summarize the diff scope so commit and PR text are accurate.
- For PRs into `dev`, expect branch protection to require these checks:
  - `Run Tests`
  - `Code Quality`
  - `Validate Branch Strategy`
- Docs-only or markdown-only PRs must still emit the required CI contexts. The repository workflow in `.github/workflows/ci.yml` intentionally runs no-op success steps when there are no code-impacting changes. Do not reintroduce path-ignore behavior that suppresses the required check names, especially now that `docs/*` is a first-class branch prefix.
- When a merge is blocked, inspect actual branch protection before guessing. Use `gh api repos/<owner>/<repo>/branches/dev/protection` or equivalent tooling to verify required contexts and review rules.
- After merge, always verify local state on `dev`, sync from origin, and ensure merged working branches are removed remotely.

## GitHub MCP and Git Workflow Guidance

- GitHub MCP is reliable for discovery and verification:
  - inspect tags, releases, commits, PR state, checks, and mergeability
  - validate historical commit targets before tagging
- GitHub MCP is not sufficient for every write action in this repository workflow:
  - create and push git tags with `git tag` + `git push`
  - use regular git branch operations for local branch creation/cleanup
  - PR merges may still require retry/fallback if GitHub branch protection or combined-status state lags
- Preferred hybrid workflow for release/tag operations:
  1. Verify remote tags/releases and target SHAs with GitHub MCP.
  2. Create annotated tags locally with git.
  3. Push tags to origin.
  4. Re-verify resulting tags with GitHub MCP.

## Pre-Production Versioning Rules

- `0.x.y` versions are pre-production milestones.
- Historical milestones currently mapped in repository docs are:
  - `0.1.0` for the MVP merge milestone
  - `0.2.0` for the QA/frontend stabilization milestone
- Reserve `1.0.0` for the first production-stable release.
- When updating docs, changelog entries, setup guides, or examples, do not reintroduce historical `1.0.0`/`1.1.0` labels for pre-production milestones.
