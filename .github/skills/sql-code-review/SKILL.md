---
name: sql-code-review
description: 'Awesome-derived SQL review skill. Use when reviewing SQL for injection risks, unparameterized queries, deadlock potential, missing transactions, unsafe bulk operations, or anti-pattern checks in queries, migrations, and data access logic.'
argument-hint: 'SQL scope, performance concerns, and risk focus'
user-invocable: true
disable-model-invocation: false
---

# SQL Code Review

Use this fallback skill for database query quality and risk review.

## Procedure
1. Review SQL statements for correctness and safety.
2. Flag injection risks, transaction pitfalls, and maintainability issues.
3. Suggest indexing and query-shape improvements where relevant.
4. Produce prioritized findings with remediation guidance.
