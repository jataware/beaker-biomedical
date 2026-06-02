# Discover the relevant projects for a disease, then query them

When the user names a disease or site ("leukemia", "breast cancer") instead of a project ID, **do not
assume `TCGA-*`.** First enumerate every project that actually contains matching cases, then run the
real query over the full set. Leukemia is a good illustration: it spans 11 projects, and the TCGA one
(`TCGA-LAML`, 200 cases) holds only ~3% of the cases — `TARGET-AML` alone has 2422.

See [../references/PROJECTS.md](../references/PROJECTS.md) for all three discovery strategies and the
`summary.case_count` caveat.

## Example

```python
import requests

S = "https://api.gdc.cancer.gov"

# 1. DISCOVER — which projects contain leukemia cases, and how many in each?
#    Facet /cases by project.project_id so the counts are the *matching* cases,
#    not whole-project totals.
disc = requests.post(f"{S}/cases", json={
    "filters": {"op": "in", "content": {"field": "disease_type", "value": ["*leukemia*"]}},
    "facets": "project.project_id",
    "size": 0,
}).json()

# invalid facet fields return HTTP 200 with a warning, not an error — check it
assert "facets" not in disc.get("warnings", {}), disc["warnings"]

buckets = disc["data"]["aggregations"]["project.project_id"]["buckets"]
project_ids = [b["key"] for b in buckets]
for b in buckets:
    print(f"{b['key']:24} {b['doc_count']:>6}")
# TARGET-AML               2422
# TARGET-ALL-P2            1587
# MP2PRT-ALL               1510
# BEATAML1.0-COHORT         780
# TCGA-LAML                 200   <- the only TCGA project; do NOT stop here
# TARGET-ALL-P3             187
# CPTAC-3                   173
# BEATAML1.0-CRENOLANIB      56
# TARGET-ALL-P1              24
# CCDI-MCI                    1
# HCMI-CMDC                   1

print(f"\n{len(project_ids)} projects contain leukemia cases")

# 2. QUERY — pull open-access RNA-Seq files across ALL discovered projects.
#    On /files, the project lives on the case: cases.project.project_id.
files = requests.post(f"{S}/files", json={
    "filters": {"op": "and", "content": [
        {"op": "in", "content": {"field": "cases.project.project_id", "value": project_ids}},
        {"op": "=",  "content": {"field": "files.experimental_strategy", "value": "RNA-Seq"}},
        {"op": "=",  "content": {"field": "files.access", "value": "open"}},
    ]},
    "fields": "file_id,file_name,cases.project.project_id",
    "size": 10000,
}).json()

print(f"{files['data']['pagination']['total']} open RNA-Seq files across {len(project_ids)} projects")
```

## Notes

- Swap the discovery filter for whatever the user described: `primary_site` (`["Breast"]`),
  `diagnoses.primary_diagnosis`, `demographic.*`, age ranges — the facet-by-project pattern is the same.
- If the user truly wants only one project, narrow *after* showing them the candidate set, or when they
  name it explicitly ("just TCGA-LAML").
- `size: 0` on the discovery call returns counts only (no records) — cheap and fast.
- For a one-off free-text starting point, `GET /v0/all?query=leukemia` returns matching projects too;
  use the real `project_id` field, not the base64 `id`.
