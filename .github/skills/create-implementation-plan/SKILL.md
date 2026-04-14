---
name: create-implementation-plan
description: 'Awesome-derived planning skill. Use when creating a new implementation plan for features, refactors, upgrades, or architecture tasks.'
argument-hint: 'Feature goal, constraints, and timeline'
user-invocable: true
disable-model-invocation: false
---

# Create Implementation Plan

Use this fallback planning skill to generate structured execution plans.

## Inputs
- Feature goal or change description
- Known constraints (schema impact, auth, filesystem, etc.)
- Timeline or release target if applicable

## Procedure
1. Restate goal, confirm scope, and call out non-goals explicitly.
2. Identify impacted layers (DB, API, storage, auth, tests, docs) and required agents.
3. Break work into ordered milestones with inter-step dependencies noted.
4. Add a risk register: likelihood, impact, and mitigation for each risk.
5. Define validation checkpoints and rollback or abort criteria per milestone.

## Output Checklist
- [ ] Goal and non-goals stated
- [ ] Impacted layers and agents identified
- [ ] Milestones ordered with dependencies
- [ ] Risks listed with mitigations
- [ ] Validation checkpoints and rollback criteria defined

## 3DKenji Example
Planning a new print-history export feature: layer impact = API (new endpoint) + storage (new frontmatter field) + tests (unit + integration); milestone 1 = storage schema + frontmatter read/write; milestone 2 = endpoint + schema; milestone 3 = test coverage + docs; risk = legacy PrintHistory.md files missing new field (mitigation: tolerant parser with default).
