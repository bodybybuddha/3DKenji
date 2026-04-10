---
name: devcontainer-mcp-bootstrap
description: 'Bootstrap and troubleshoot 3DKenji developer environment tooling, especially devcontainer and MCP startup. Use when onboarding, fixing missing tools, validating mcp.json/settings, or resolving startup/runtime configuration drift.'
argument-hint: 'Environment/setup issue, expected behavior, and observed errors'
---

# Devcontainer and MCP Bootstrap

## When to Use
- New contributor setup and first-run verification.
- Missing tooling in devcontainer.
- MCP servers fail to install, start, or auto-start.
- Workspace configuration drift across Docker/devcontainer files.

## Procedure
1. Validate runtime prerequisites and command availability.
2. Confirm container build files include required dependencies.
3. Check workspace MCP configuration and startup settings.
4. Fix path, command, or environment variable issues.
5. Verify with reproducible startup and health checks.
6. Document the final setup and troubleshooting steps.

## Output Checklist
- Root cause summary
- Config changes applied
- Verification commands and outcomes
- Ongoing maintenance recommendations
