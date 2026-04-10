---
name: secret-scanning
description: 'Awesome-derived skill for repository secret hygiene. Use when scanning staged changes or files for tokens, passwords, API keys, and credential leaks before merge/release.'
argument-hint: 'Scope to scan and remediation strictness'
user-invocable: true
disable-model-invocation: false
---

# Secret Scanning

Use this fallback skill to prevent credential leaks.

## Procedure
1. Scan changed files and configs for credential patterns.
2. Validate findings and classify true vs false positives.
3. Replace exposed values with secure references or env vars.
4. Summarize findings and mitigation status.
