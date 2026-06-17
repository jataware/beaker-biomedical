# Verify against the live source — don't trust the docs

The defining discipline of these skills. Load this before writing any factual guidance (fields,
values, counts, error behavior) into a skill. The rule: **introspection tells you what is
*defined*; only probing tells you what *works*.**

## Why

Upstream docs drift, omit whole query families, describe a template schema that isn't populated,
or document an endpoint that 404s in production. A prior hand-authored skill can be wrong the same
way. Every factual claim in a skill — a field name, a value's casing, a base URL, a count — must
be confirmed by hitting the live API, or it is a guess.

## What to confirm, always

- **The production base URL** (and whether paths are version-pinned). Probe it; don't copy from a
  blog.
- **Real field and value names, and their casing.** `vital_status` is `dead`/`alive` lowercase, not
  `Deceased`. `project_id` is `TCGA-BRCA`, dash-separated and case-sensitive. Confirm each backticked
  identifier you write.
- **Representative counts**, captured into examples ("breast spans ~20 projects, FM-AD 2583,
  TCGA-BRCA 1098…"). They make rules credible and let the agent self-check.
- **Error behavior**, because the failure modes *are* the gotchas: does an invalid facet 400, or
  200 with empty `aggregations` + a `warnings` key? Is the API POST-only and a GET rejected? Does
  it need a `variables` key in the body even when empty?
- **Silent defaults.** The Portal shows only Cancer Gene Census genes by default (22,638→716); a
  search defaults to `size=10`. A skill that misses these ships a silent trap.

## For GraphQL / Bento-style commons

1. Introspect the live schema: `{ __schema { queryType { fields { name } } } }`. The docs (and a
   prior skill) routinely miss an entire query layer.
2. **Probe each query family — defined ≠ working.** On a prototype commons a schema can define 74
   queries while only the ~9 Elasticsearch-backed ones answer and everything node-level errors with
   a dead-backend message. Classify working-vs-erroring from probing and say so plainly; do not
   present the full schema as usable.
3. Note the per-framework quirks you hit (POST-only, mandatory `variables` key, the facet bucket
   count field being `cases`/`subjects` not `count`) as critical rules.

## Turn surprises into critical rules

Every time the live API contradicts the docs or your expectation, that delta is the most valuable
content in the skill. Promote it to a **Critical rule** (cross-cutting) or a **Gotcha** (local),
stated as a procedure with the verified number attached. The mutation-frequency denominator
(`case_filters` not `filters`; cohort frequency collapses to nonsense otherwise) is the archetype:
nobody guesses it, and it silently produces a plausible wrong answer.

## Capture, then preserve

- Put verified numbers and the exact working call into `examples/`.
- Copy the upstream OpenAPI/SDL/man-pages into `assets/` **verbatim** so the skill is
  self-contained — never link out to a `raw_docs/` dump that won't ship.
- Validate at the end: grep every backticked field/value in the skill against the live catalogue.
  An invented field is a defect even if it reads plausibly.
