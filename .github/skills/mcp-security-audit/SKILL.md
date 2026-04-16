---
name: mcp-security-audit
description: 'Awesome-derived skill for auditing MCP server configuration security. Use for secret exposure checks, unpinned versions, risky args, and server trust review in mcp.json files.'
argument-hint: 'MCP config files and security constraints to audit'
user-invocable: true
disable-model-invocation: false
---

# MCP Security Audit

Use this as a fallback governance skill when reviewing MCP configuration risks.

## Procedure
1. Inspect MCP server definitions for hardcoded secrets and unsafe arguments.
2. Flag unpinned package versions and risky command patterns.
3. Verify least-privilege environment usage.
4. Provide remediation patches and a risk-ranked summary.
