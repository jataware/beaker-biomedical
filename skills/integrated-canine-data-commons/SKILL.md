---
name: integrated-canine-data-commons
description: >-
  Query, search, and build cohorts from canine (dog) cancer studies in the NCI Integrated Canine
  Data Commons (ICDC) GraphQL API — a Cancer Research Data Commons (CRDC) repository of comparative
  oncology data where naturally-occurring dog cancers serve as models for human cancer. Use when the
  user needs to find programs/studies (COP, CMCP, PRECINCT, CSU FACC, PCCR; osteosarcoma, glioma,
  melanoma, lymphoma, mammary/bladder cancer, etc.); build a case cohort by breed, diagnosis, sex,
  disease site, stage, study, or sample/file type; pull per-case clinical, demographic, diagnosis,
  enrollment, sample, or biospecimen metadata; retrieve longitudinal clinical-trial data (visits,
  cycles, adverse events, vital signs, physical exams, disease extent, prior therapy/surgery); map
  one dog (canine individual) across multiple studies; list files and get their CRDC DRS IDs / build
  a download manifest for the Cancer Genomics Cloud; or run ad-hoc GraphQL against the ICDC schema.
compatibility: Python 3 with the `requests` package. No API key, token, or login required — ICDC is fully open-access. The API serves metadata/search only; file bytes are downloaded out-of-band via CRDC DRS or the Cancer Genomics Cloud (all current ICDC files are Open-access).
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# Integrated Canine Data Commons (ICDC) API

The NCI **Integrated Canine Data Commons** is the comparative-oncology repository in the Cancer
Research Data Commons (CRDC). It harmonizes data from naturally-occurring cancers in pet dogs —
treated as spontaneous models for the corresponding human cancers — so researchers can find canine
studies, build cohorts, pull clinical/biospecimen metadata, and stage files for cloud analysis. Its
GraphQL API is the programmatic interface behind `caninecommons.cancer.gov`. As of this writing ICDC
holds **5 programs, 18 studies, 1,029 cases, 1,613 samples, 3,010 files, ~41.9 TB** (call the
metrics queries below for live totals; data model v2.1.0 / schema `2.0.0`).

**Endpoint:** `https://caninecommons.cancer.gov/v1/graphql/` — a **single GraphQL endpoint, POST-only.**
There is no REST API; every operation is a GraphQL query against this one URL.

## Authentication

**None.** All ICDC metadata, search, and (currently) all data files are open-access — no API key,
token, cookie, or login. See [auth.yaml](auth.yaml). The API returns metadata only; it does not stream
file bytes. Files carry a CRDC **DRS** id (`dg.4DFC/<uuid>`) and an `s3://` location; you download them
out-of-band via DRS or by exporting a manifest to the **Cancer Genomics Cloud (CGC)**. See
[references/FILES.md](references/FILES.md).

## Calling it (POST only)

```python
import requests
URL = "https://caninecommons.cancer.gov/v1/graphql/"      # trailing slash; POST only
requests.post(URL, json={"query": "{ numberOfStudies numberOfCases volumeOfData }"})
```

A **GET is rejected** (`{"errors":[{"message":"API will only accept POST requests"}]}`) — unlike some
sibling commons, ICDC has no GET path. Responses are JSON: `{"data": {...}}` on success,
`{"errors":[...]}` on failure, and **HTTP 200 even on query errors** — always inspect `errors`. See
[examples/quickstart.md](examples/quickstart.md).

## Three query layers (pick the right one)

ICDC exposes 125 root queries in three families — see [references/QUERIES.md](references/QUERIES.md):

1. **Portal faceted search (Elasticsearch-backed)** — the cohort-building entry point. `searchCases`
   returns repository counts **and** per-facet group counts across 18 dimensions (breed, diagnosis,
   sex, disease site, stage, study, sample/file type…); `caseOverview` / `sampleOverview` /
   `fileOverview` return the matching paged rows for the same filters; `globalSearch` is free-text;
   `createManifest` builds a file manifest. See [references/SEARCH.md](references/SEARCH.md).
2. **Auto-generated node queries** — one per data-model node (`program`, `study`, `case`, `sample`,
   `file`, `demographic`, `diagnosis`, `cohort`, `study_arm`, `visit`, `cycle`, `adverse_event`, …),
   each taking exact-match property args **and** a rich `filter` object + `first`/`offset`/`orderBy`.
   Best for precise graph traversal. See [references/ENTITIES.md](references/ENTITIES.md).
3. **Cypher-backed convenience queries** — pre-joined combos like `studiesByProgram`, `caseDetail`,
   `studyDetail`, `filesOfCase`, `samplesByCaseId`, `fileDetail`, `multiStudyCases`, the
   per-study `*NodeData` clinical tables, and the `numberOf*` / `*CountOf*` metrics.

## Critical rules

- **POST only; HTTP 200 on errors.** A GET returns an error, not data. Query errors come back with
  HTTP 200 and an `errors` array — `raise_for_status()` won't catch them; always inspect `errors`.
- **Know the ID keys — they're not interchangeable.** Programs key on `program_acronym` (e.g. `COP`);
  studies on **`clinical_study_designation`** (e.g. `OSA01`, `COTC022`) — the `study_code` argument
  also accepts the numeric `accession_id` (e.g. `000006`); cases on `case_id` (e.g. `COTC021-0101`,
  study-prefixed); files on `uuid` / `file_uuid`. Resolve the right key first (via `studiesByProgram`,
  `program`, `searchCases`) before a per-entity pull. See [references/ENTITIES.md](references/ENTITIES.md).
- **Default page size differs by layer.** Portal `*Overview` / `globalSearch` default to **`first: 10`**
  — set it or silently get 10 rows. Auto-generated **node queries have no default limit** — `{ case { case_id } }`
  returns **all 1,029**; set `first` to cap large nodes. See [references/PAGINATION.md](references/PAGINATION.md).
- **`searchCases` itself is not paged and returns no row data** — it returns counts + facet group
  counts + the full `caseIds`/`sampleIds`/`fileIds` arrays. Feed those IDs (or the same filter args)
  into `caseOverview`/`sampleOverview`/`fileOverview` to get paged rows. See [references/SEARCH.md](references/SEARCH.md).
- **Empty result ≠ "filter is right, data is absent."** Facet/filter values are controlled
  vocabularies (e.g. `study_type` is `Clinical Trial` / `Genomics` / `Transcriptomics` / combos;
  `sex`, `breed`, `disease_site`…). A misspelled or wrong-cased value yields an empty list with **no
  error**. Discover valid values from `searchCases` facet counts first; don't hardcode a guess.
- **Some nodes are empty or deprecated — and `numberOfAliquots` is always 0.** ICDC has **no aliquot
  data loaded** (every `aliquot*` count returns 0), and the `agent`, `agent_administration`,
  `follow_up`, `off_study`, `off_treatment`, `lab_exam`, `image`, and `assay` nodes are placeholders
  with little or no data in current studies. An empty return from these is expected, not a bug.
- **Don't invent fields or query names.** The schema is fixed (125 queries). An unknown field returns
  a `Validation error (FieldUndefined)`. The full catalogue is
  [assets/query-fields.txt](assets/query-fields.txt) + [references/QUERIES.md](references/QUERIES.md);
  introspect a type with `{ __type(name:"case"){ fields { name } } }` when unsure.
- **The API never downloads bytes.** It returns the DRS id + `s3://` location; fetch via CRDC DRS
  (`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`) or stage a manifest into the Cancer Genomics Cloud.
  See [references/FILES.md](references/FILES.md).

## Building a cohort (the common task — don't assume one study)

When the user names a cancer, breed, or trait rather than a study code, start at `searchCases` to see
the facet landscape (which breeds/diagnoses/studies actually exist and their case counts), narrow with
the facet arguments, then pull rows with `caseOverview`/`sampleOverview`/`fileOverview` and a manifest
with `createManifest`. See [examples/faceted_search.md](examples/faceted_search.md).

## Data model

```
program ──< study ──< study_arm ──< cohort ──< case ──< { demographic, diagnosis, enrollment,
                 │                                   │      sample, file, visit, registration }
                 ├──< { human_relevance, study_site, principal_investigator, publication, file }
                 └  case ──> canine_individual   (one dog across multiple studies)
visit ──> cycle ;  { sample, physical_exam, vital_signs, disease_extent } ──> visit
{ prior_therapy, prior_surgery } ──> enrollment ;  file ──> { sample, diagnosis, case, study }
```

`case_id` joins per-case records; `clinical_study_designation` joins per-study records; the
`canine_individual` node links study-specific cases that are the same physical dog (18 cases
participate in multiple studies). The `human_relevance` node ties each study to the human cancer it
models. Full node/field/relationship breakdown: [references/ENTITIES.md](references/ENTITIES.md).

## Example usage

The smallest useful query — live repository totals, no auth:

```python
import requests
r = requests.post("https://caninecommons.cancer.gov/v1/graphql/",
                  json={"query": "{ numberOfPrograms numberOfStudies numberOfCases numberOfSamples numberOfFiles volumeOfData schemaVersion }"})
print(r.json()["data"])
# {'numberOfPrograms': 5, 'numberOfStudies': 18, 'numberOfCases': 1029, 'numberOfSamples': 1613,
#  'numberOfFiles': 3010, 'volumeOfData': 4.185e13, 'schemaVersion': '2.0.0'}
```

For complete worked examples see [examples/](examples/):

- [quickstart.md](examples/quickstart.md) — the POST request helper, error handling, metrics.
- [discover_studies.md](examples/discover_studies.md) — programs/studies via `studiesByProgram` + `globalSearch`.
- [faceted_search.md](examples/faceted_search.md) — `searchCases` facets → cohort → `caseOverview` rows.
- [case_clinical.md](examples/case_clinical.md) — one case's clinical detail via `caseDetail` + node queries.
- [files_and_download.md](examples/files_and_download.md) — case/study files → DRS id → manifest → Cancer Genomics Cloud.
- [clinical_node_data.md](examples/clinical_node_data.md) — per-study longitudinal clinical tables (`*NodeData`).
- [multi_study_individual.md](examples/multi_study_individual.md) — map one dog across studies via `multiStudyCases` / `canine_individual`.

## References

- [references/QUERIES.md](references/QUERIES.md) — the 125 queries grouped by family: arguments,
  return types, which to use when, and the internal/empty ones to skip. The endpoint catalogue.
- [references/ENTITIES.md](references/ENTITIES.md) — data model, every node + its fields, the ID keys
  and how to resolve them, relationships, and node-query usage. Load before scoping a per-entity pull.
- [references/SEARCH.md](references/SEARCH.md) — `searchCases` (the 18 facet dimensions, count vs
  filterCount), the `*Overview` row queries, `globalSearch`. Load for any cohort/discovery task.
- [references/PAGINATION.md](references/PAGINATION.md) — `first`/`offset`/`orderBy`, the per-layer
  default-page-size footgun, and the node-query `filter` operators (`_in`, `_contains`, AND/OR/NOT…).
- [references/FILES.md](references/FILES.md) — file records, the DRS `dg.4DFC/` id, `acl`/Open access,
  `createManifest` (builds CSV) vs the interoperation `storeManifest` (signed URL), the CGC workflow.
- [references/CLINICAL.md](references/CLINICAL.md) — the per-study `*NodeData` clinical-trial tables
  (visits, cycles, adverse events, vitals, disease extent, prior therapy/surgery) and node counts.

Upstream specs are preserved verbatim in [assets/](assets/): `icdc-model.yml` (data model),
`search-schema.graphql` (the faceted-search API), `interoperation-openapi.yaml` (the manifest→CGC
service), and `query-fields.txt` (the full introspected query list).
