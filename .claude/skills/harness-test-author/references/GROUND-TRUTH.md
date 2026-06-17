# Live-verifying ground truth

Every number, ID, or set you bake into a `number` / `regex` / `set_contains` check must be obtained
from the live API before you write it down — not from the docs, not from memory, not from the
rationale you imagined. Load this before filling in target values.

## Get the value with the skill's own method

Run the exact method the skill prescribes, against the live API, and read the real result. If the
skill says "facet `/cases` by `project.project_id`", do that — don't approximate with a different
call that might count differently.

```python
import requests
r = requests.post("https://api.gdc.cancer.gov/cases",
    json={"filters": {"op": "in", "content": {"field": "primary_site", "value": ["Breast"]}},
          "facets": "project.project_id", "size": 0})
buckets = r.json()["data"]["aggregations"]["project.project_id"]["buckets"]
print(len(buckets))                       # -> the count to put in count_at_least / number
print([b["key"] for b in buckets][:5])    # -> the IDs for set_contains
```

Two reasons it must be the skill's method, not just *a* method: (1) it confirms the skill actually
leads here, and (2) different methods legitimately return different denominators (the
mutation-frequency `case_filters`-vs-`filters` split is the canonical example) — you want the number
the *correct* method produces, which is also the number the trap does *not*.

## Counts drift — grade by tolerance, record the date

CRDC counts move with data releases. So:

- Never use `exact: true` for a live count. Use `tolerance_percent` (typically 10–15) or
  `tolerance_absolute`. Reserve `exact` for things that don't drift (a fixed enumeration, a
  structural number).
- Put the verified value and the date in `rationale.md` so the next author knows what "current"
  meant. (It's not graded, but it's the audit trail.)
- If a `number` check later starts failing because the data moved, re-probe and re-baseline the
  target — don't widen the tolerance until it's meaningless.

## Encode the trap from the same probe

While you have the live data, capture the **wrong** answer too — the number the trap produces — and
encode it as `must_not_contain`. Verifying both the right and wrong values from one session is the
cheapest way to be sure the check actually discriminates.

## IDs and patterns

For ID checks, confirm the real format from a live record (`PDC000123`, `dg.4DFC/<uuid>`,
`TCGA-BRCA`) and prefer a `regex` for the shape plus a `substring`/`set_contains` for a specific
known ID. Don't invent an ID format from the docs.
