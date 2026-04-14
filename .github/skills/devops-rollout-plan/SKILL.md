---
name: devops-rollout-plan
description: 'Awesome-derived release rollout skill. Use for deployment sequencing, verification signals, rollback planning, and communication checklists.'
argument-hint: 'Target environment, rollout risk, and rollback tolerance'
user-invocable: true
disable-model-invocation: false
---

# DevOps Rollout Plan

Use this fallback skill for controlled deployment planning.

## Inputs
- Target environment and current version
- Change description and risk level
- Rollback tolerance (can revert DB? can revert filesystem?)

## Procedure
1. Define rollout phases: preflight, deploy, verify, close — with responsible owner per phase.
2. List preflight checks: migrations safe to run, secrets in place, health endpoints ready.
3. Specify go/no-go criteria and observable verification signals per phase.
4. Define rollback sequence: what to revert, in what order, and who approves.
5. Produce a communication checklist: who to notify at start, on success, and on rollback.

## Output Checklist
- [ ] Rollout phases and owners defined
- [ ] Preflight checks listed
- [ ] Go/no-go criteria and verification signals specified
- [ ] Rollback sequence documented
- [ ] Communication checklist complete

## 3DKenji Example
Rolling out a new Alembic migration adding a `tags` table: preflight = run `alembic upgrade head` on staging and verify schema; go/no-go = all integration tests pass post-migration; rollback = `alembic downgrade -1` restores prior state (verified via downgrade test); notify = confirm deploy in team channel after green health check.
