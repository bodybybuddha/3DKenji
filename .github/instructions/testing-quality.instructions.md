---
description: "Use when adding or modifying tests, validating feature readiness, or running quality gates in 3DKenji."
name: "Testing and Quality Gates"
applyTo: "tests/**/*.py"
---
# Testing and Quality Gates

- Match test scope to change scope: unit for logic, integration for workflows, e2e for user-critical flows.
- Prefer deterministic fixtures and explicit assertions over timing-dependent tests.
- Keep regression coverage for any behavior change.

## Validation Checklist

1. Run targeted tests for changed modules first.
2. Run broader suites when changes cross boundaries.
3. Report commands run and outcomes clearly.
4. Do not treat uninvestigated failing tests as acceptable.
