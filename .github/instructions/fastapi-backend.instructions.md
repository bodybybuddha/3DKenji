---
description: "Use when editing FastAPI backend code, including routers, schemas, services, and request/response behavior in 3DKenji."
name: "FastAPI Backend Standards"
applyTo: "src/backend/**/*.py"
---
# FastAPI Backend Standards

- Keep endpoint logic thin and push business logic into service modules.
- Use explicit request validation and predictable error responses.
- Preserve ownership and permission checks on protected resources.
- Maintain type hints and clear function boundaries.

## Change Checklist

1. Update endpoint, schema, and service flow consistently.
2. Cover success and failure paths with tests.
3. Confirm no sensitive data is leaked in logs or error payloads.
4. Document externally visible behavior changes.
