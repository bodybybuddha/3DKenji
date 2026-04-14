---
name: create-specification
description: 'Awesome-derived spec authoring skill. Use when drafting a new feature or system specification aligned to implementation and testing workflows.'
argument-hint: 'Problem statement, users, and expected outcomes'
user-invocable: true
disable-model-invocation: false
---

# Create Specification

Use this fallback skill to produce implementation-ready specifications.

## Inputs
- Problem statement and user or system context
- Known constraints or non-goals
- Desired outcomes or success criteria

## Procedure
1. Restate the problem in one sentence and confirm scope boundaries.
2. Enumerate functional requirements (what the system must do).
3. Enumerate non-functional requirements (performance, security, compatibility).
4. Define acceptance criteria — each must be objectively testable.
5. Identify open questions, assumptions, and out-of-scope items.

## Output Checklist
- [ ] Problem statement confirmed
- [ ] Functional requirements listed
- [ ] Non-functional requirements listed
- [ ] Acceptance criteria are testable
- [ ] Open questions and assumptions documented

## 3DKenji Example
Specifying a new `GET /projects/{id}/tags` endpoint: problem = tag retrieval is missing; functional = return tag list for a project; non-functional = response under 100 ms for ≤500 tags; acceptance = 200 with tag array, 404 for unknown project, 403 for unauthorized caller.
