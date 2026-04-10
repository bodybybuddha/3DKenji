---
name: playwright-generate-test
description: 'Awesome-derived Playwright test generation skill. Use to convert user scenarios into stable browser tests for critical workflows.'
argument-hint: 'User flow scenario, selectors, and pass criteria'
user-invocable: true
disable-model-invocation: false
---

# Playwright Generate Test

Use this fallback skill to bootstrap browser test coverage from scenarios.

## Procedure
1. Translate scenario into concrete steps and assertions.
2. Generate Playwright tests with deterministic waits.
3. Add failure diagnostics and cleanup where needed.
4. Report run results and flaky-risk notes.
