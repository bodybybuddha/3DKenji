---
name: project-storage-frontmatter
description: 'Maintain and evolve 3DKenji project filesystem behavior and markdown frontmatter handling. Use when changing ProjectInfo.md, PrintHistory.md, storage paths, slug/category moves, or metadata parsing/rendering.'
argument-hint: 'Storage/frontmatter change request and compatibility expectations'
---

# Project Storage and Frontmatter

## When to Use
- Adjust storage path or directory lifecycle logic.
- Change frontmatter schema or parsing behavior.
- Update ProjectInfo.md or PrintHistory.md generation and rendering.
- Diagnose compatibility issues in existing project folders.

## Procedure
1. Trace DB-to-filesystem lifecycle and identify affected path rules.
2. Define backward compatibility behavior for existing project directories.
3. Implement parser/serializer updates with strict but practical validation.
4. Preserve frontmatter separation from rendered markdown body.
5. Add or update tests with real-world fixture cases.
6. Document migration guidance for metadata or path changes.

## Output Checklist
- Storage behavior changes
- Compatibility impact
- Test coverage updates
- Migration guidance (if needed)
