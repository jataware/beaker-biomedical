# Discovering relevant projects

A common mistake when querying GDC is hard-coding `TCGA-BRCA` (or any lone `TCGA-*`
project) because it appears in tutorials. **TCGA is not the dataset — it is one program among many.**
A cancer type, anatomical site, or clinical cohort almost always spans several programs. If you filter
on one guessed `project_id`, you silently miss most of the matching data.

When the user names a disease, site, or cohort rather than an explicit project ID, your **first** step
is to enumerate the projects that actually match, then filter downstream queries on the full set.

## Snapshot of Projects

Captured 2026-06-02 against GDC API v2.2.0 (`GET /projects?size=0` and `facets=program.name`). The
catalogue grows over time; re-run these to refresh.

- **91 projects** across **26 programs**. TCGA accounts for **33** of the 91 projects — the other 58
  live under MATCH (17), TARGET (9), CGCI (4), CMI (3), APOLLO, BEATAML1.0, CPTAC, MP2PRT (2 each),
  and 17 single-project programs (FM, HCMI, MMRF, NCICCR, OHSU, ORGANOID, WCDT, REBC, CCDI, …).
- **Breast** cases live in **20 projects**, not 1. TCGA-BRCA (1098 cases) is outnumbered by FM-AD
  (2583) and joined by CMI-MBC, CPTAC-2, CPTAC-3, HCMI-CMDC, CCDI-MCI, nine MATCH arms, and more.
- **Leukemia** spans **11 projects**. TCGA-LAML has 200 cases; TARGET-AML has 2422, TARGET-ALL-P2
  1587, MP2PRT-ALL 1510, BEATAML1.0-COHORT 780. Defaulting to TCGA would return ~3% of the cases.

## Program list

`GET https://api.gdc.cancer.gov/projects?size=0&facets=program.name`. Projects-per-program, 2026-06-02:

| Program | Projects | Program | Projects |
|---|---|---|---|
| TCGA | 33 | MP2PRT | 2 |
| MATCH | 17 | ALCHEMIST, CCDI, CCG, CDDP_EAGLE, | 1 each |
| TARGET | 9 | CTSP, EXCEPTIONAL_RESPONDERS, FM, | |
| CGCI | 4 | HCMI, MMRF, NCICCR, OHSU, ORGANOID, | |
| CMI | 3 | RC, REBC, TRIO, VAREPOP, WCDT | |
| APOLLO, BEATAML1.0, CPTAC | 2 each | | |

## Three ways to discover projects

Pick by what the user gave you. All are open-access (no token).

### 1. By anatomical site or disease — query `/projects`

Projects carry list-valued `primary_site` and `disease_type` fields. Filter on them to get the
matching projects plus their program and total size.

```python
import requests
r = requests.post("https://api.gdc.cancer.gov/projects",
    json={
        "filters": {"op": "in", "content": {"field": "primary_site", "value": ["Breast"]}},
        "fields": "project_id,name,program.name,summary.case_count",
        "sort": "summary.case_count:desc",
        "size": 100,
    })
for h in r.json()["data"]["hits"]:
    print(h["project_id"], h["program"]["name"], h.get("summary", {}).get("case_count"))
```

> **Caveat — `summary.case_count` is the *whole-project* count, not your filtered count.** A project
> appears here if *any* of its cases match (e.g. TCGA-SKCM surfaces for `primary_site=Breast` because a
> few melanoma cases are sited there), but `case_count` reports all 470 SKCM cases, not the breast
> subset. To get the real per-project match count, use strategy 2.

### 2. By clinical filter, with real per-project counts — facet `/cases`

This is the **preferred** approach for cohort building: it returns the exact number of *matching*
cases in each project, using the same filter you will reuse downstream.

```python
import requests
r = requests.post("https://api.gdc.cancer.gov/cases",
    json={
        "filters": {"op": "in", "content": {"field": "primary_site", "value": ["Breast"]}},
        "facets": "project.project_id",
        "size": 0,                       # counts only, no records
    })
data = r.json()
assert "facets" not in data.get("warnings", {}), data["warnings"]   # invalid facets return 200
buckets = data["data"]["aggregations"]["project.project_id"]["buckets"]
project_ids = [b["key"] for b in buckets]
# FM-AD 2583, TCGA-BRCA 1098, CMI-MBC 200, CPTAC-2 134, HCMI-CMDC 69, ... (20 projects)
```

`project_ids` is now the full set to feed into your `/files` or `/cases` filter. Any clinical filter
works here — `disease_type`, `diagnoses.primary_diagnosis`, `demographic.*`, age ranges, etc.

### 3. By free text — quicksearch `/v0/all`

When the user gives an ambiguous term and you are not yet sure of the field or vocabulary value:

```python
import requests
r = requests.get("https://api.gdc.cancer.gov/v0/all", params={"query": "breast", "size": 10})
for h in r.json()["data"]["query"]["hits"]:
    if "project_id" in h:
        print(h["project_id"], h["name"], h.get("primary_site"), h.get("disease_type"))
```

> Quicksearch hits carry a base64 `id` (e.g. `UHJvamVjdDpUQ0dBLUJSQ0E=`). Use the real `project_id`
> field for follow-up calls, never the base64 `id`.

## Browsing the controlled vocabularies

`primary_site` and `disease_type` are controlled vocabularies — a guessed value that isn't in the
vocabulary matches nothing (and as a facet returns 200 with empty buckets, not an error). List the
valid values before filtering:

```python
import requests
# All site / disease / program values that actually exist, with project counts
r = requests.get("https://api.gdc.cancer.gov/projects",
                 params={"facets": "primary_site,disease_type,program.name", "size": 0})
aggs = r.json()["data"]["aggregations"]
for b in aggs["primary_site"]["buckets"]:
    print(b["key"], b["doc_count"])
```

`GET /projects/_mapping` lists every filterable/faceted project field. See [FIELDS.md](FIELDS.md) for
the `/_mapping` workflow and [FACETS.md](FACETS.md) for facet field names and the empty-bucket failure
mode.

## Discover, then query

The whole point is to feed discovered IDs into the real query. The clean pattern:

```python
import requests
S = "https://api.gdc.cancer.gov"

# 1. discover every project with leukemia cases
disc = requests.post(f"{S}/cases", json={
    "filters": {"op": "in", "content": {"field": "disease_type", "value": ["*leukemia*"]}},
    "facets": "project.project_id", "size": 0}).json()
project_ids = [b["key"] for b in disc["data"]["aggregations"]["project.project_id"]["buckets"]]
# ['TARGET-AML', 'TARGET-ALL-P2', 'MP2PRT-ALL', 'BEATAML1.0-COHORT', 'TCGA-LAML', ...] — 11 projects

# 2. pull open RNA-Seq files across ALL of them, not just TCGA-LAML
files = requests.post(f"{S}/files", json={
    "filters": {"op": "and", "content": [
        {"op": "in", "content": {"field": "cases.project.project_id", "value": project_ids}},
        {"op": "=",  "content": {"field": "files.experimental_strategy", "value": "RNA-Seq"}},
        {"op": "=",  "content": {"field": "files.access", "value": "open"}},
    ]},
    "fields": "file_id,file_name,cases.project.project_id",
    "size": 10000}).json()
print(files["data"]["pagination"]["total"], "files across", len(project_ids), "projects")
```

See [../examples/discover_projects_for_disease.md](../examples/discover_projects_for_disease.md) for a
fuller worked recipe.

## Caveats

- **Project IDs are case-sensitive and dash-separated.** `TCGA-BRCA`, not `tcga_brca` or `TCGA_BRCA`.
- **`summary.case_count` (project) ≠ facet count (cases).** The former is whole-project; the latter is
  your filter's match count. Use strategy 2 for accurate cohort sizes.
- **`primary_site` and `disease_type` are list-valued and controlled.** A project can list many sites;
  a wrong value silently matches nothing. Browse the vocabulary (above) before filtering.
- **`cases.project.project_id` on `/files` vs `project.project_id` on `/cases`/`/projects`.** Mirror
  the data model — project lives on the case from the files endpoint. See [FILTERS.md](FILTERS.md).
- **Only narrow to a single project when the user names it explicitly** ("just TCGA-BRCA") or after you
  have shown the candidate set and they have chosen.
