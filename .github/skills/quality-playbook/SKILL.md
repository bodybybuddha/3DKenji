---
name: quality-playbook
description: 'Awesome-derived quality system skill. Use for building repeatable quality gates, spec-to-test traceability, and structured review protocols for delivery readiness.'
argument-hint: 'Change scope, quality target, and release confidence bar'
user-invocable: true
disable-model-invocation: false
---

# Quality Playbook

Use this fallback skill to structure quality beyond single test runs.

## Inputs
- Change scope (files, layers, behaviors changed)
- Quality target (e.g. regression-safe, release-ready, exploratory)
- Known gaps or flaky areas

## Procedure
1. Define quality objectives and acceptance thresholds for this change.
2. Map each requirement or behavior change to a test layer: unit, integration, contract, e2e.
3. Identify existing coverage gaps and assign owners or blockers.
4. Run the relevant test suite tiers and collect pass/fail evidence.
5. Produce a release confidence report: what passed, what is deferred, and what is a hard blocker.

## Output Checklist
- [ ] Quality objectives defined
- [ ] Requirements mapped to test layers
- [ ] Gaps and flaky tests identified
- [ ] Test suite results captured
- [ ] Release confidence verdict with blockers and deferred items

## 3DKenji Example
Quality gate for a new project ownership transfer endpoint: unit = service logic for ownership swap; integration = DB state after transfer; contract = response shape matches schema; e2e = full transfer flow via API; gap = no negative test for unauthorized caller — add before marking release-ready.
