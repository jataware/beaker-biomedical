# Splitting a monolithic SKILL.md into references + examples

A worked before/after of the refactor in [references/STRUCTURE.md](../references/STRUCTURE.md).
Use this when a `SKILL.md` (or a doc dump you're converting) is too long.

## Before — everything inline (excerpt)

```markdown
## Filtering
The filters parameter is a nested JSON object. Operators are =, !=, <, <=, >, >=, in, exclude,
excludeifany, is, not, and, or. Here is the full table of every operator with examples...
[40 lines of operator table]
Here is how to filter breast cases: first you POST to /cases with a facet on project.project_id,
then you read the buckets, here is the full script... [25 lines]
Note that exclude vs excludeifany differ on list-valued fields: exclude drops a record only when
every element matches... [15 lines]
```

That's three different roles mashed together: a reference table, a worked recipe, and a gotcha.

## After

**In `SKILL.md`** — one rule, one gotcha, two pointers:

```markdown
## Filter syntax
`filters` is a nested JSON of operators over `{field, value}`. Same shape on every endpoint.
Operators: `=, !=, <, …, in, exclude, excludeifany, is, not, and, or`; `*` wildcards in `value`.
See [references/FILTERS.md](references/FILTERS.md) when constructing or debugging a filter.

- **`exclude` vs `excludeifany`** differ only on list-valued fields: `exclude` drops a record when
  *every* element matches; `excludeifany` when *any* does.
- **Don't default to TCGA** — discover the project set first:
  [examples/discover_projects_for_disease.md](examples/discover_projects_for_disease.md).
```

**In `references/FILTERS.md`** — the full operator table, `is missing` semantics, payload examples.

**In `examples/discover_projects_for_disease.md`** — the runnable facet-then-filter recipe with the
verified counts.

## Why this is better, not just shorter

- The 40-line table no longer costs tokens on every activation — only when a filter is actually
  being built.
- The recipe became a named, adaptable pattern instead of prose buried mid-section.
- `SKILL.md` now reads as *what will silently go wrong + where to look*, which is its whole job.

The content is identical; only its **disclosure level** changed. Never delete real content to
shorten a `SKILL.md` — relocate it (the one exception: delete blocks that re-teach general
knowledge the model already has).
