---
name: alembic-migration-safety
description: 'Plan and implement safe SQLAlchemy plus Alembic schema changes in 3DKenji. Use when adding columns/tables/indexes, changing constraints, or evolving data models with migration safety checks.'
argument-hint: 'Schema change requested, compatibility needs, and data safety constraints'
---

# Alembic Migration Safety

## When to Use
- Modify SQLAlchemy models.
- Create or update Alembic migrations.
- Change indexes, constraints, or relationships.
- Review migration rollback and data-loss risk.

## Procedure
1. Map requested schema changes to model definitions and migration history.
2. Decide compatibility strategy: additive first, backfill, then tighten constraints if needed.
3. Create or edit migration scripts with explicit upgrade and downgrade paths.
4. Validate model and migration alignment.
5. Run migration checks in a safe environment and verify key query paths.
6. Document any irreversible or high-risk operations.

## Output Checklist
- Model changes
- Migration changes
- Upgrade and downgrade notes
- Data risk notes
