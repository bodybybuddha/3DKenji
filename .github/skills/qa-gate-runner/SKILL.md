---
name: qa-gate-runner
description: 'Run 3DKenji quality gates across unit, contract, integration, validation, and E2E coverage. Use when verifying feature readiness, triaging flaky tests, or preparing merge/release checks.'
argument-hint: 'Change summary, risk areas, and required quality gate depth'
---

# QA Gate Runner

## When to Use
- Validate feature changes before merge.
- Diagnose failing or flaky tests.
- Confirm release readiness based on test evidence.
- Enforce minimum test coverage for changed behavior.

## Procedure
1. Classify change type and choose required test layers.
2. Run targeted tests first for quick feedback.
3. Run broader suites for regression confidence.
4. Investigate failures and separate product bugs from test instability.
5. Improve tests for determinism and actionable failures.
6. Produce a pass/fail gate verdict with evidence.

## Output Checklist
- Suites run and results
- Failure triage summary
- Coverage or confidence assessment
- Release gate verdict
