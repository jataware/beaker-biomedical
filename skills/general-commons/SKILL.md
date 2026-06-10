---
name: general-commons
description: >-
  Query and search study, participant, sample, clinical, and file metadata from the NCI General
  Commons (GC), formerly the Cancer Data Service (CDS) — the data-type-agnostic CRDC repository for
  NCI-funded studies that don't fit a specialized commons. Use when the user names General Commons,
  CDS, the Cancer Genomics Cloud (CGC) / Velsera, or a GC program (CCDI, CPTAC-on-GC, HTAN, PDXNet,
  Kids First, TCIA Radiology, DCCPS, MP2PRT, NCIcaNano); to list programs/studies, pull per-study
  participants, diagnoses, treatments, samples, or files; resolve a study's phs_accession; or run
  ad-hoc GraphQL against the GC schema. LOWER PRIORITY / fallback — GC mirrors data from other
  commons. For genomics use `genomic-data-commons`, for proteomics `proteomic-data-commons`, for
  imaging the imaging-data-commons; only pick GC when the data lives only in GC or the user explicitly
  asks for General Commons / CDS. For an ambiguous query, prefer the more specific data commons.
compatibility: Python 3 with the `requests` package. No API key, token, or login required — the GC GraphQL API is open-access for all metadata/search. The API does not download data files; controlled-access data access requires dbGaP authorization and happens on the Cancer Genomics Cloud (CGC by Velsera).
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# General Commons (GC) API

The NCI **General Commons** (GC, formerly the **Cancer Data Service / CDS**) is the data-type-agnostic
repository in the Cancer Research Data Commons (CRDC). It stores studies from NCI-funded programs whose
data don't fit the requirements of a specialized commons (Genomic, Proteomic, Imaging, …). Its GraphQL
API exposes study, program, subject/participant, clinical, biospecimen, sequencing, imaging,
proteomics, and file metadata across all GC studies. As of this writing GC holds **9 programs, 89
studies, ~120,900 subjects, ~109,500 samples, ~615,800 files, ~111,500 images** (call the metrics
queries below for live totals; GraphQL schema `3.1.0`, data model `8.0.1`, data release `12.0.0`).

**Endpoint:** `https://general.datacommons.cancer.gov/v1/graphql/` — a **single GraphQL endpoint**
(trailing slash matters). A GET returns the schema; POST a `{"query": "..."}` body to run queries.
There is no REST API.

## Two query families (pick the right one)

GC is a Bento-framework commons exposing **73 queries** in two families — see [references/QUERIES.md](references/QUERIES.md):

1. **Faceted search (Elasticsearch-backed)** — the cohort-building entry point, centered on the
   **subject**. `searchSubjects` returns repository counts **and** per-facet group counts across ~40
   dimensions (diagnosis, sex, sample type, experimental strategy, study, …); `subjectOverview` /
   `sampleOverview` / `fileOverview` / `protocolOverview` return the matching paged rows for the same
   filters; `filesInList` builds a download manifest with DRS URIs. See [references/SEARCH.md](references/SEARCH.md).
2. **Data Type Queries (Gen3-style)** — untransformed per-study records: `programs`, `studies`,
   `participants`, `diagnoses`, `treatments`, `samples`, `files`, `genomic_info`, `proteomics`, `pdx`,
   the imaging-modality nodes, and the caNanoLab nodes (`investigators`, `characterizations`,
   `publications`, `protocols`, `compositions`, `consent_groups`). Most require `phs_accession`.

Plus repository **metrics** (`numberOfStudies`/`numberOfSubjects`/`numberOfSamples`/`numberOfFiles`/
`numberOfImages`/`numberOfProteomics`/`numberOfDiseaseSites`), per-entity `*Count` queries, `version`,
and discovery helpers (`globalSearch`, `programList`, `studyList`, `programDetail`, `studyDetail`,
`subjectDetail`).

## When to use this skill (read first — GC is a fallback)

GC is **lower priority** than the specialized commons and largely *mirrors* data submitted elsewhere.
Route the query to the most specific commons:

- Genomics (mutations, expression, BAMs, copy number, TCGA/TARGET/…) → **`genomic-data-commons`**.
- Proteomics (mass-spec quantitation, CPTAC proteome/phospho) → **`proteomic-data-commons`**.
- Imaging (radiology/pathology image *pixels*) → the **imaging-data-commons**.

Use GC **only** when: the user explicitly names General Commons / CDS / the Cancer Genomics Cloud; the
study/program lives only in GC (e.g. caNanoLab/NCIcaNano nanomaterials, some CCDI/DCCPS/PDXNet studies);
or you've confirmed the data isn't in a specialized commons. **For any ambiguous request, pick the more
specific commons** and only fall back to GC if it comes up empty.

## Authentication

**None for the API.** All GC *metadata and search* (every query here) is open-access — no API key,
token, cookie, or login. See [auth.yaml](auth.yaml).

The API returns metadata only; it **does not download data files**. Open-access *data* is public;
controlled-access (sensitive) *data* requires dbGaP authorization, and the files are accessed on the
**Cancer Genomics Cloud (CGC) by Velsera** via an exported manifest — not by direct download. See
[references/FILES.md](references/FILES.md).

## Calling it (GET vs POST)

```python
import requests
URL = "https://general.datacommons.cancer.gov/v1/graphql/"   # trailing slash matters
requests.post(URL, json={"query": "{ studiesCount programsCount }"})   # default for real work
requests.get(URL, params={"query": "{ studiesCount }"})                # fine for short queries
```

Responses are JSON: `{"data": {...}}` on success, `{"errors": [...]}` on failure. GC returns **HTTP 200
even on query errors** — always inspect `errors`. See [examples/quickstart.md](examples/quickstart.md).

## Critical rules

- **`phs_accession` is REQUIRED on almost every per-study query.** `participants`, `samples`, `files`,
  `diagnoses`, `treatments`, `genomic_info`, `images`, `proteomics`, `pdx`, and every per-study
  `*Count` need it; omitting it is a hard error, not an empty result. Only `programs`, `studies`,
  `version`, and the global counts (`programsCount`/`studiesCount`/`versionsCount`) take no
  `phs_accession`. **So resolve the study's `phs_accession` first** (via `studies` / `programs`) before
  any clinical/file pull. See [references/ENTITIES.md](references/ENTITIES.md).
- **`first` defaults to 10 — set it or silently get 10 rows.** Pagination is required: `first` (page
  size, **max 10000**, default 10) and `offset` (default 0). A 1102-participant study returns 10 unless
  you raise `first` or loop. See [references/PAGINATION.md](references/PAGINATION.md).
- **Every field comes back as a String** — even counts and sizes (`number_of_participants: "1102"`,
  `file_size: "25920500"`). Cast to int/float yourself; don't assume numeric JSON types.
- **The API does not download data.** `File.file_url_in_cds` is frequently empty and `file_id` is a CRDC
  **DRS** identifier (e.g. `dg.4DFC/<uuid>`), not an HTTP link. Data access is via the Cancer Genomics
  Cloud using a manifest; controlled data needs dbGaP authorization. Never promise a direct download.
  See [references/FILES.md](references/FILES.md).
- **Don't invent fields or query names.** The schema is fixed; an unknown field returns an `errors`
  block. The catalogue is [references/QUERIES.md](references/QUERIES.md); introspect with
  `{ __type(name:"File"){ fields { name } } }` when unsure.
- **"subject" (faceted search) and "participant" (Data Type Queries) are the same entity — two views,
  not two datasets.** Pick the family by task: the **subject** queries (`searchSubjects`,
  `subjectOverview`, `numberOfSubjects`) are the cohort-builder — filter across studies by
  characteristic, get facet counts. The **participant** Data Type Queries (`participants`, `diagnoses`,
  `treatments`, `samples`, `files`) are for pulling the structured records of a known study by
  `phs_accession`. A typical flow is `searchSubjects`/`subjectOverview` to find the cohort, then the
  Data Type Queries (or `phs_accession`) to pull its full records. See [references/SEARCH.md](references/SEARCH.md).
- **In the faceted layer, each facet bucket's count field is `subjects`, not `count`** (`GroupCount {
  group subjects }`). Asking for `count` there is a `FieldUndefined` error.

## Discovering studies & programs

When the user names a disease, program, or topic rather than a `phs_accession`, enumerate first. List
programs with `programs` (or the convenient UI helper `programList { acronym name num_studies }`); list
or filter studies with `studies(study_acronyms / study_names / phs_accessions)`; or free-text search
everything with `globalSearch(input: "...")`. Studies carry `study_data_types`, `study_access`
(Open/Controlled), and counts — use these to decide whether GC is even the right commons (if it's a
pure genomics/proteomics study, redirect to the specialized commons). See
[references/DISCOVERY.md](references/DISCOVERY.md) and
[examples/discover_studies.md](examples/discover_studies.md).

## Query catalogue

Full arguments and returned fields are in [references/QUERIES.md](references/QUERIES.md); the per-node
field lists are in [references/ENTITIES.md](references/ENTITIES.md) and
[references/DATA-TYPES.md](references/DATA-TYPES.md).

| Family | Queries |
|---|---|
| **Faceted search** (ES) → [SEARCH.md](references/SEARCH.md) | `searchSubjects` (counts + facets), `subjectOverview`, `sampleOverview`, `fileOverview`, `protocolOverview`, `filesInList`, `fileIDsFromList`, `idsLists`, `findSubjectIdsInList` |
| Metrics | `numberOfStudies`, `numberOfSubjects`, `numberOfSamples`, `numberOfFiles`, `numberOfImages`, `numberOfProteomics`, `numberOfDiseaseSites` |
| Data Type — program / study | `programs`, `studies` |
| Data Type — clinical / biospecimen (per study) | `participants`, `diagnoses`, `treatments`, `samples` |
| Data Type — files & sequencing | `files`, `genomic_info` |
| Data Type — proteomics / PDX | `proteomics`, `pdx` |
| Data Type — imaging modalities | `images`, `multiplex_microscopies`, `non_dicomct_images`, `non_dicommr_images`, `non_dicompet_images`, `non_dicom_pathology_images`, `non_dicom_radiology_all_modalities` |
| Data Type — caNanoLab / study extras | `investigators`, `characterizations`, `publications`, `protocols`, `compositions`, `consent_groups` |
| Counts | `programsCount`, `studiesCount`, `versionsCount` (no args); per-study `*Count` (require `phs_accession`) |
| Version | `version`, `schemaVersion`, `schemaModelVersion` |
| Detail / discovery helpers | `globalSearch`, `programList`, `studyList`, `programDetail`, `studyDetail`, `subjectDetail`, `samplesForSubjectId` |

## Argument syntax

GraphQL named arguments inside the query, not a JSON `filters` document. Strings double-quoted, ints
bare, list args in `[...]`:

```graphql
{ files(phs_accession: "phs001287" file_types: ["bam"] first: 50 offset: 0)
  { file_id file_name file_type file_size md5sum } }
```

## Data model

```
program ──< study ──< participant ──< { sample, diagnosis, treatment }
                 │                          └──< { pdx, characterization, publication, composition }
                 ├──< file ──< { genomic_info, proteomic, image, multiplex_microscopy, non_dicom* }
                 └──< { investigator, protocol, consent_group }
```

`phs_accession` (the dbGaP study accession, e.g. `phs001287`; a few studies use a non-`phs` key like a
DOI) is the join key tying every per-study record to its study. Files use DRS-style `file_id`s. Full
breakdown and per-entity ID list: [references/ENTITIES.md](references/ENTITIES.md).

## Example usage

The smallest useful query — live repository totals + data release, no auth:

```python
import requests
r = requests.post("https://general.datacommons.cancer.gov/v1/graphql/",
                  json={"query": "{ studiesCount programsCount version { data_version datetime } }"})
print(r.json()["data"])
# {'studiesCount': 89, 'programsCount': 9, 'version': {'data_version': '12.0.0', 'datetime': '2026-05-06T...'}}
```

For complete worked examples see [examples/](examples/):

- [quickstart.md](examples/quickstart.md) — GET vs POST, the request helper, error handling.
- [discover_studies.md](examples/discover_studies.md) — Programs/studies, `globalSearch`, deciding if GC is the right commons.
- [faceted_search.md](examples/faceted_search.md) — `searchSubjects` facets → cohort → `subjectOverview`/`fileOverview` rows.
- [study_clinical.md](examples/study_clinical.md) — `phs_accession` → participants + diagnoses + treatments + samples.
- [files_for_study.md](examples/files_for_study.md) — List a study's files, the DRS `file_id` / `drs_uri`, and why there's no direct download.
- [paginate.md](examples/paginate.md) — `first`/`offset` loop for a full result set.

## References

- [references/QUERIES.md](references/QUERIES.md) — Every query: arguments (required vs optional),
  returned type, notes. The endpoint catalogue.
- [references/SEARCH.md](references/SEARCH.md) — The faceted-search family: `searchSubjects` and its
  ~40 facet dimensions, `subjectCountBy*` vs `filterSubjectCountBy*` vs `donutCountBy*`, the
  `*Overview` row queries, `GroupCount.subjects`. Load for any cohort/cross-study search.
- [references/ENTITIES.md](references/ENTITIES.md) — Data model, `phs_accession` as the join key, the
  per-entity ID list and full field lists for Program/Study/Participant/Sample/Diagnosis/Treatment/
  File, subject-vs-participant terminology. Load before scoping a per-study query.
- [references/PAGINATION.md](references/PAGINATION.md) — `first`/`offset`, the 10000 cap, the
  default-10 footgun, loop patterns.
- [references/FILES.md](references/FILES.md) — File records, the DRS `file_id` / `drs_uri`, open vs
  controlled access, dbGaP authorization, the Cancer Genomics Cloud (CGC) manifest workflow, why the
  API never downloads.
- [references/DISCOVERY.md](references/DISCOVERY.md) — Finding studies/programs, `globalSearch`,
  `study_data_types`, and how to decide GC vs a specialized commons.
- [references/DATA-TYPES.md](references/DATA-TYPES.md) — The per-file/per-sample modality nodes
  (`genomic_info`, `proteomic`, `images`, `pdx`, `multiplex_microscopy`, `non_dicom*`, caNanoLab
  `characterizations`/`compositions`) and what each carries.

Upstream specs are preserved verbatim in [assets/](assets/): `general-commons-schema.graphql` (the
backend GraphQL schema — the authoritative API surface), `es-indices.yaml` (the Elasticsearch index
definitions behind the faceted search) + `es-indices-legacy.yml` and `es-index-spec-context.md`,
`query-fields.txt` (the full introspected query list), and `api-documentation.md` (the upstream prose doc).
