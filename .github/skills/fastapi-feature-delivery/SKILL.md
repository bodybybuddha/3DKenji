---
name: fastapi-feature-delivery
description: 'Implement or modify FastAPI features in 3DKenji, including endpoints, schemas, service wiring, and behavior tests. Use when adding API routes, changing request/response models, or updating business logic.'
argument-hint: 'Feature goal, affected endpoints, constraints, and acceptance criteria'
---

# FastAPI Feature Delivery

## When to Use
- Add new API endpoints.
- Change endpoint behavior or validation.
- Update service-layer logic tied to API routes.
- Refactor API code while preserving contract behavior.

## Procedure
1. Identify affected files under API routers, schemas, and services.
2. Define acceptance criteria and expected request/response behavior.
3. Implement endpoint and service changes with explicit validation and error handling.
4. Add or update tests for both success and failure paths.
5. Run targeted tests, then broader regression checks if needed.
6. Summarize changed behavior, contract impact, and follow-ups.

## Output Checklist
- Clear behavior summary
- Contract compatibility notes
- Test results
- Risks or TODOs
