---
name: auth-permissions-hardening
description: 'Harden authentication and authorization in 3DKenji. Use when changing JWT flows, API keys, ownership checks, permission enforcement, secret handling, or security-sensitive request paths.'
argument-hint: 'Auth/security change request, threat concerns, and affected endpoints'
---

# Auth and Permissions Hardening

## When to Use
- Modify login, registration, token, or API key behavior.
- Change ownership or permission checks.
- Review sensitive flows for leakage or bypass risks.
- Add denial-path and abuse-case coverage.

## Procedure
1. Identify trust boundaries and sensitive data paths.
2. Define explicit allow and deny conditions.
3. Implement changes with least-privilege defaults.
4. Ensure logs and errors do not leak secrets or sensitive internals.
5. Add tests for both successful and denied access paths.
6. Summarize residual risks and operational safeguards.

## Output Checklist
- Security behavior updates
- Threat cases covered
- Test outcomes
- Residual risk notes
