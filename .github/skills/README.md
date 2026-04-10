# Copilot Skills Index

These skills are installed for this workspace under `.github/skills/` and load on demand.

## Priority Model

1. Custom project skills are the primary set and should be used first.
2. Awesome-derived skills are installed as fallback helpers and can now auto-trigger when relevant.

## Custom Skills (Primary)

1. `fastapi-feature-delivery`
   - Path: `./fastapi-feature-delivery/SKILL.md`
   - Use for: endpoint, schema, and service behavior changes
2. `alembic-migration-safety`
   - Path: `./alembic-migration-safety/SKILL.md`
   - Use for: SQLAlchemy/Alembic schema and migration safety work
3. `project-storage-frontmatter`
   - Path: `./project-storage-frontmatter/SKILL.md`
   - Use for: filesystem paths, frontmatter parsing, and project metadata files
4. `auth-permissions-hardening`
   - Path: `./auth-permissions-hardening/SKILL.md`
   - Use for: JWT/API key/permission and security-sensitive changes
5. `qa-gate-runner`
   - Path: `./qa-gate-runner/SKILL.md`
   - Use for: layered quality gates and release test readiness
6. `release-docs-sync`
   - Path: `./release-docs-sync/SKILL.md`
   - Use for: README/docs/spec/changelog synchronization
7. `devcontainer-mcp-bootstrap`
   - Path: `./devcontainer-mcp-bootstrap/SKILL.md`
   - Use for: devcontainer and MCP setup/bootstrap troubleshooting

## Awesome-Derived Skills (Fallback)

1. `mcp-security-audit` – `./mcp-security-audit/SKILL.md`
2. `secret-scanning` – `./secret-scanning/SKILL.md`
3. `quality-playbook` – `./quality-playbook/SKILL.md`
4. `create-implementation-plan` – `./create-implementation-plan/SKILL.md`
5. `update-implementation-plan` – `./update-implementation-plan/SKILL.md`
6. `create-specification` – `./create-specification/SKILL.md`
7. `update-specification` – `./update-specification/SKILL.md`
8. `devops-rollout-plan` – `./devops-rollout-plan/SKILL.md`
9. `playwright-generate-test` – `./playwright-generate-test/SKILL.md`
10. `webapp-testing` – `./webapp-testing/SKILL.md`
11. `sql-code-review` – `./sql-code-review/SKILL.md`
12. `postgresql-optimization` – `./postgresql-optimization/SKILL.md`

## Usage

- Skills can be invoked with slash commands by skill name in chat.
- Example invocations: `/qa-gate-runner`, `/mcp-security-audit`.
- Skills are discovered and loaded only when relevant, not all at once.
