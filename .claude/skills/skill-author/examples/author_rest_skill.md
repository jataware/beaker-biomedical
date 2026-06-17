# Authoring a REST/Python skill from an OpenAPI spec

Walks the procedure for a REST API with an OpenAPI document, modeled on
`skills/genomics-data-commons`. The point is the *order*: probe first, then write only what the
probing taught you.

## 1. Probe before writing

Confirm the base URL, a real field, its value casing, and the error behavior — live, from a
throwaway script. Don't transcribe these from the spec.

```python
import requests
# Base URL + the default-size trap: no `size` silently caps at 10 even when total is millions.
r = requests.post("https://api.gdc.cancer.gov/cases",
    json={"filters": {"op": "in", "content": {"field": "primary_site", "value": ["Breast"]}},
          "facets": "project.project_id", "size": 0})
buckets = r.json()["data"]["aggregations"]["project.project_id"]["buckets"]
print(len(buckets), buckets[:3])
# → 20 projects, FM-AD 2583, TCGA-BRCA 1098, … : "breast == TCGA-BRCA" is wrong. That's a Critical rule.

# Invalid facet behavior — does it 400, or 200 with a warning? (It 200s. That's a Gotcha.)
r = requests.post("https://api.gdc.cancer.gov/cases",
    json={"facets": "diagnoses.tumor_stage", "size": 0})
print("aggregations" in r.json()["data"], r.json().get("warnings"))
```

## 2. What survives into SKILL.md

Only the cross-cutting, every-invocation material — each line earned by step 1:

- Base URL + the auth boundary (open vs token-gated operations).
- **Critical rules:** use POST for non-trivial searches; `size` defaults to 10; don't default to
  TCGA — discover the project set first; don't invent fields (hit `/_mapping`).
- One endpoint summary table.
- **Gotchas:** invalid facets 200 with empty `aggregations` + a `warnings` key; the
  mutation-frequency denominator comes from `case_filters`, not `filters`.
- Pointers, each with a load-trigger.

## 3. What moves out

- Full operator table, `is missing` semantics → `references/FILTERS.md`.
- `/_mapping`, field groups → `references/FIELDS.md`.
- The discover-then-query recipe with the verified counts → `examples/discover_projects_for_disease.md`.
- The upstream `gdcapi.yaml` → `assets/` verbatim.

## 4. auth.yaml

Open data needs nothing; only controlled-access downloads need a token:

```yaml
credentials:
  - name: GDC_TOKEN
    check: env_var
    required: false
    description: Only for controlled-access downloads / BAM slicing / submission. Open endpoints work without it.
    usage: "HTTP header `X-Auth-Token: <token>`"
    service: "https://portal.gdc.cancer.gov/"
```

## 5. Validate

`python ../scripts/validate_skill.py skills/genomics-data-commons`, then grep every backticked
field (`cases.project.project_id`, `is_cancer_gene_census`, …) against `/_mapping` to confirm none
were invented.
