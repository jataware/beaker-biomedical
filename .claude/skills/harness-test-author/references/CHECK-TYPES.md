# Check types

`eval.yaml` is a top-level `checks:` list. Each item is a **single-key map** keyed by the check
type — a scalar for simple checks, an inline list for the multi-string ones, a nested map for the
rest. Load this when writing checks.

```yaml
checks:
  - substring: "Cisplatin"
  - substring_any: [dead, deceased]                 # also substring_all, must_not_contain
  - regex: 'PDC\d{6}'                               # or {name: ids, pattern: 'PDC\d{6}'}
  - number: {name: deceased_subjects, target: 8556, tolerance_percent: 15}
  - set_contains: {name: top_genes, members: [TP53, CDKN2A]}
  - count_at_least: {name: projects, min: 10}       # judged
  - behavior: used case_filters for the cohort denominator, not filters   # judged
```

## Deterministic — matched against the final answer string, no LLM

| Type | Shape | Passes when |
|---|---|---|
| `substring` | scalar | the (case-insensitive) string appears in the answer |
| `substring_any` | inline list | at least one listed string appears |
| `substring_all` | inline list | every listed string appears |
| `must_not_contain` | inline list | none of the listed strings appear (encodes the trap) |
| `regex` | scalar, or `{name, pattern}` | the pattern matches somewhere in the answer |
| `number` | `{name, target, <tolerance>}` | some number parsed from the answer is within `target ± tolerance` |
| `set_contains` | `{name, members: [...]}` | every member string appears in the answer |

**`number` tolerances** (pick one; never bare equality for live counts):
`tolerance_percent: 15` · `tolerance_absolute: 50` · `tolerance_pp: 2` (percentage points) ·
`exact: true` (only for values that genuinely never drift — IDs as numbers, fixed enumerations).

## Semantic — graded by `--judge-model`

| Type | Shape | Judge decides, reading… |
|---|---|---|
| `behavior` | scalar (the assertion prose) | the **transcript** (final answer + every step's code with clipped stdout) |
| `count_at_least` | `{name, min}` | the **final answer only**: does it enumerate ≥ `min` distinct items |

The judge is strict and literal and conservative — if the evidence doesn't clearly support the
claim, it fails. So write a `behavior` as **one decidable claim**, not a compound sentence:

- Good: `filtered on species = human in addition to vital_status`
- Good: `called column_values('vital_status') to confirm the value before filtering`
- Bad: `correctly discovered the projects and computed the right frequency and explained the census` (three claims; split them)

## Choosing the right type

- A **method** claim ("used `case_filters`, not `filters`"; "declined and redirected to GDC") is
  invisible in the final answer — it lives in the code. It **must** be `behavior` (the only check
  that sees the transcript). A `substring` can't catch it.
- A **result** claim (a count, an ID, a gene set) is in the answer text → deterministic
  (`number`/`regex`/`set_contains`/`substring*`).
- The **trap** (the plausible wrong number, the "here's your downloaded file" hallucination) →
  `must_not_contain`.
- "At least N things" where the items are free-form prose → `count_at_least` (judged); if they're
  matchable strings, prefer `set_contains` (deterministic, cheaper, no judge needed).

A test passes when every **scored** check passes. Deterministic checks always score; semantic
checks are left unscored under `--no-judge`. See
[WHAT-REACHES-THE-AGENT-AND-JUDGE.md](WHAT-REACHES-THE-AGENT-AND-JUDGE.md) for exactly what evidence
each grader sees.
