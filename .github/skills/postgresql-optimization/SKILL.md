---
name: postgresql-optimization
description: 'Awesome-derived PostgreSQL optimization skill. Use when investigating slow queries, missing indexes, N+1 patterns, EXPLAIN/EXPLAIN ANALYZE results, sequential scans, index bloat, connection pooling, or vacuum tuning in 3DKenji.'
argument-hint: 'Query/workload context and performance target'
user-invocable: true
disable-model-invocation: false
---

# PostgreSQL Optimization

Use this fallback skill for Postgres-specific tuning and analysis.

## Procedure
1. Identify slow query paths and access patterns.
2. Recommend index and query-shape optimizations.
3. Evaluate tradeoffs for write cost, storage, and concurrency.
4. Summarize optimization plan with validation steps.
