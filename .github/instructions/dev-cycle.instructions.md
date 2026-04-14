---
description: "Use when committing current changes, creating PRs, merging into dev/main, or performing tag/release operations for 3DKenji."
name: "3DKenji Dev Cycle"
---
# 3DKenji Dev Cycle

## Purpose

Capture the repository-specific rules that caused previous commit/PR/merge/tag operations to become discovery exercises.

## Commit and PR Flow

- Always inspect current branch, working tree, and diff scope before branching or committing.
- For PRs targeting `dev`, branch names must use one of:
  - `feature/*`
  - `bugfix/*`
  - `docs/*`
  - `chore/*`
- Do not commit directly to `dev` or `main`.
- Standard sequence:
  1. `git checkout dev && git pull origin dev`
  2. `git checkout -b <allowed-prefix>/<slug>`
  3. run secret scan on staged changes before committing (invoke `secret-scanning` skill)
  4. commit focused changes
  5. `git push -u origin <branch>`
  6. create PR to `dev`
  7. wait for required checks
  8. merge PR
  9. return to `dev`, pull, and delete merged branch remotely/local if still present

## Required Checks and Branch Protection

- The `dev` branch requires these status checks:
  - `Run Tests`
  - `Code Quality`
  - `Validate Branch Strategy`
- The CI workflow is intentionally written so docs-only PRs still publish successful `Run Tests` and `Code Quality` contexts.
- If a PR shows green visible jobs but merge is still blocked, inspect branch protection and combined status before retrying.

## GitHub MCP Usage Rules

- Use GitHub MCP for:
  - checking existing tags/releases
  - validating commit SHAs
  - reading PR state and check runs
  - verifying merge results after the fact
- Do not rely on GitHub MCP alone for:
  - creating git tags
  - pushing refs
  - local branch cleanup
- Use git/gh CLI for repo mutations when MCP lacks the needed write capability.

## Tag and Release Flow

- Verify existing remote tags first.
- For 3DKenji pre-production history:
  - `v0.1.0` corresponds to the MVP merge milestone
  - `v0.2.0` corresponds to the QA/frontend stabilization milestone
- Preferred sequence:
  1. verify tags/releases with MCP
  2. verify target commits with MCP
  3. create annotated tags with git
  4. push tags
  5. re-check tags with MCP

## Failure Handling

- If merge is blocked, do not guess. Inspect:
  - PR check runs
  - combined status
  - branch protection rules
- If docs-only PRs fail to satisfy required contexts, inspect `.github/workflows/ci.yml` before retrying the merge.
- If a shell session closes unexpectedly during cleanup, re-run only the missing cleanup step and then verify branch state.
