# Roadmap

## Release Track

- 0.1.0: MVP baseline (completed)
- 0.2.0: QA and frontend stabilization (completed)
- 0.3.0: Filesystem architecture hardening and admin policy follow-up (in progress)
- 1.0.0: First production-stable public release (scope locked)

## In Flight (0.3.0)

- Admin UI for project deletion policy management
- Documentation governance cleanup and consistency enforcement
- Bug tracking normalization and branch traceability improvements
- Path hygiene pass for open-source docs portability

## 1.0.0 Scope Lock (Must-Have)

- Complete OAuth login providers (GitHub, Google) with clear account-linking behavior
- Preserve admin recovery path without OAuth (local credential login and recovery flow)
- Fully wire and validate API key authentication/authorization behavior end-to-end
- Close known API key scope validation gap and ship regression coverage
- Keep delivery focus on stability, quality gates, and release readiness over UI cosmetics

## Post-1.0 Backlog

- Cloud storage backends (S3, Azure Blob)
- Plugin capability expansion for media/viewers
- Additional performance and observability hardening
- Cosmetic/UX enhancements that do not block production readiness

## Contributor Workflow

- Add new feature ideas here at roadmap level.
- Break accepted features into specs/<id>/spec.md, plan.md, and tasks.md.
- Keep CHANGELOG.md strictly user-facing at release cut time.
