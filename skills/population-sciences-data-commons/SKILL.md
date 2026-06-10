---
name: population-sciences-data-commons
description: >-
  Query the NCI Population Sciences Data Commons (PS-DC) GraphQL API — a Cancer Research Data Commons
  (CRDC) repository for large population-science screening cohorts/trials run by DCCPS. It currently
  holds three studies: NLST (National Lung Screening Trial), PLCO (Prostate, Lung, Colorectal and
  Ovarian Cancer Screening Trial), and PBCS (Polish Breast Cancer Study). Use when the user needs to
  explore these studies — study metadata, design, enrollment years, dbGaP accessions, participant
  demographics (age/sex/race/ethnicity breakdowns), cancer primary sites/morphology, data-collection
  categories, study-level data files (with DRS ids), or a faceted study search. NOTE: PS-DC is a NEW,
  undocumented, best-effort PROTOTYPE; today it answers STUDY-LEVEL queries only (participant-,
  sample-, and file-record-level queries are defined but currently error — see below). For
  participant-level genomics/proteomics/imaging or general CDS data, use the other CRDC commons.
compatibility: Python 3 with the `requests` package. No API key, token, or login required — PS-DC metadata is open-access. The API serves metadata only; study files carry CRDC DRS ids for out-of-band download.
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# Population Sciences Data Commons (PS-DC) API

The NCI **Population Sciences Data Commons** is a Cancer Research Data Commons (CRDC) repository for
large **population-science screening cohorts and trials** (NCI Division of Cancer Control and
Population Sciences, DCCPS). Its GraphQL API is the programmatic interface behind
`populationsciences.datacommons.cancer.gov`. It is a **Bento-framework** commons (like General Commons,
ICDC, and CTDC).

It currently holds **3 studies, ~205,000 participants** (live via `globalStatsBar`):

| `study_short_name` | Study | Design | Participants |
|---|---|---|---|
| `NLST` | National Lung Screening Trial | Clinical Trial | 48,860 |
| `PLCO` | Prostate, Lung, Colorectal and Ovarian Cancer Screening Trial | Cohort Study – Prospective | 151,383 |
| `PBCS` | Polish Breast Cancer Study | Case-Control Study | 4,886 |

> **This is a NEW, undocumented, best-effort PROTOTYPE.** There is no upstream documentation; this
> skill is built entirely from live introspection and probing (verified ~June 2026). Behavior — and
> especially which queries work — will change. Re-probe before trusting specifics.

**Endpoint:** `https://populationsciences.datacommons.cancer.gov/v1/graphql/` — a **single GraphQL
endpoint, POST-only**. No REST API.

## Authentication

**None.** Metadata/search is open-access — no key, token, or login. See [auth.yaml](auth.yaml). The API
returns metadata only; study files carry a CRDC **DRS** id (`dg.4DFC/<uuid>`) for out-of-band download.

## Calling it (two non-obvious request rules)

```python
import requests
URL = "https://populationsciences.datacommons.cancer.gov/v1/graphql/"   # trailing slash; POST only
requests.post(URL, json={"query": "{ globalStatsBar { study_short_name number_of_participants } }",
                         "variables": {}})                              # variables key REQUIRED
```

- **POST only.** A GET is rejected (`"API will only accept POST requests"`).
- **The body MUST include a `variables` key** (even `{}`). Omitting it is a hard error
  (`Cannot invoke "java.util.Map.keySet()" because "variables" is null`), not an empty result.
- **HTTP 200 even on query errors** — always inspect `errors`.

See [examples/quickstart.md](examples/quickstart.md).

## ⚠️ What works today: STUDY-LEVEL queries only

The schema exposes 74 queries, but on the deployed prototype the **participant-, sample-, file-record-,
and node-level queries currently error** with `Unable to connect to localhost:7687` — their **Neo4j
backend is unreachable**. Only the **Elasticsearch-backed STUDY-LEVEL queries answer**. Verified live:

| Status | Queries |
|---|---|
| ✅ **Working** (study-level, ES) | `globalStatsBar`, `searchStudies`, `tabStudy`, `studyDemographics`, `primarySiteMorphology`, `dataCollectionPage`, `studyGeneral`, `studyFiles`, `minMaxBoundQuery` |
| ❌ **Currently error** (Neo4j down) | `schemaVersion`; every node query (`study`, `program`, `diagnosis`, `sample`, `file`, `demographic_data`, …); `subjectList*`, `subjectCountBy*FromLists`, `subjectInfo`, `fileInfo`, `fileOverview`, `nodeCounts`, `armInfo`, `programArms`, `idsLists`, `findIdsFromLists`, `groupCount`, `groupList` |

So: **answer study-level questions** (what studies, their design/size/demographics/sites/files). If the
user wants participant- or specimen-level records, say those endpoints exist in the schema but are not
currently functional, and retry later — don't fabricate. Full annotated catalogue:
[references/QUERIES.md](references/QUERIES.md) and [assets/query-fields.txt](assets/query-fields.txt).

## Critical rules

- **POST + `variables` key required; HTTP 200 on errors.** See "Calling it."
- **Most of the schema is currently non-functional** (Neo4j down) — see the table above. Treat an
  `Unable to connect to localhost:7687` error as "this endpoint isn't live yet," not a query mistake.
- **Group/facet bucket counts use the field `subjects`, not `count`** (`GroupCount`/`GroupCounts {
  group subjects }`). And in the study-level facets `subjects` often means **number of studies**
  (e.g. `studyCountByStudyDesign`), not people — read it in context.
- **The schema is a breast-cancer-flavored Bento template.** Subject-level facets like `er_status`,
  `pr_status`, `recurrence_score`, `chemotherapy_regimen`, `menopause_status`, `tumor_grade` exist in
  the schema (the `subjectListBy*` / `subjectCountBy*` families) but are (a) not currently queryable
  and (b) unlikely to be populated for screening cohorts like NLST/PLCO. Don't present them as
  available PS-DC dimensions.
- **No auth, but no participant download either.** `studyFiles` returns study-level files (data
  dictionaries, manifests) with a DRS id (`dg.4DFC/<uuid>` / `drs_uri`) and `data_file_access_control`
  (e.g. `Open Access`); resolve bytes via CRDC DRS. The bulk participant data lives in dbGaP under each
  study's `dbgap_accession_id`. See [references/STUDIES.md](references/STUDIES.md).
- **Don't invent fields or query names.** Unknown fields return `Validation error (FieldUndefined)`;
  scalar fields that are objects return `SubselectionRequired` (e.g. `participant_sexes` is
  `[GroupCounts]` — select `{ group subjects }`). Introspect with the `variables` key:
  `{ __type(name:"TabStudy"){ fields { name } } }`.

## Query families

- **Study overview / metadata:** `globalStatsBar` (the home-page study cards), `tabStudy` (the rich
  study table), `studyDemographics` (age/sex/race/ethnicity breakdowns), `primarySiteMorphology`
  (cancer sites + morphology codes), `dataCollectionPage` (data-collection categories), `studyGeneral`
  (personnel/publications/links), `studyFiles` (study-level files + DRS), `minMaxBoundQuery` (slider
  bounds). See [references/STUDIES.md](references/STUDIES.md).
- **Faceted study search:** `searchStudies` → `SearchResult` with `studyCountBy*` /
  `filterStudyCountBy*` facets (study design, neoplasm site, country, data-collection, biospecimen,
  race/ethnicity/sex) and numeric ranges. See [references/SEARCH.md](references/SEARCH.md).
- **(Defined but currently erroring):** the subject/sample/file/node families — see the table above.

## Example usage

The smallest useful query — the studies and their sizes, no auth:

```python
import requests
r = requests.post("https://populationsciences.datacommons.cancer.gov/v1/graphql/",
                  json={"query": "{ globalStatsBar { study_short_name number_of_participants "
                                 "study_design cancer_type_count } }", "variables": {}})
print(r.json()["data"]["globalStatsBar"])
# [{'study_short_name': 'NLST', 'number_of_participants': 48860, 'study_design': 'Clinical Trial', ...},
#  {'study_short_name': 'PLCO', 'number_of_participants': 151383, ...},
#  {'study_short_name': 'PBCS', 'number_of_participants': 4886, ...}]
```

For complete worked examples see [examples/](examples/):

- [quickstart.md](examples/quickstart.md) — the POST helper (with `variables`), the working-vs-erroring split, error handling.
- [explore_studies.md](examples/explore_studies.md) — `globalStatsBar`, `tabStudy`, `studyDemographics`, `primarySiteMorphology`, `studyFiles`.
- [search_studies.md](examples/search_studies.md) — `searchStudies` faceted study search.

## References

- [references/QUERIES.md](references/QUERIES.md) — all 74 queries annotated **working vs currently-erroring**, with arguments and return types. The endpoint catalogue.
- [references/STUDIES.md](references/STUDIES.md) — the 3 studies and the study-level metadata model: every working study query, its return type fields, and the `dbgap_accession_id` handoff.
- [references/SEARCH.md](references/SEARCH.md) — `searchStudies` / `SearchResult`: the `studyCountBy*` vs `filterStudyCountBy*` facets, numeric ranges, and the `subjects`-means-studies caveat.

Self-contained specs from live introspection (no upstream repo exists) are in [assets/](assets/):
`query-fields.txt` (the 74 queries, annotated) and `schema-types.txt` (every object type and its fields).
