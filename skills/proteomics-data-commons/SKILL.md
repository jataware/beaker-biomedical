---
name: proteomic-data-commons
description: >-
  Query, search, and download cancer proteomics data from the NCI Proteomic Data Commons (PDC)
  GraphQL API. Use when the user needs to find programs/projects/studies or cases in CPTAC, ICPC,
  APOLLO, or other PDC programs; pull clinical, biospecimen, sample/aliquot, or experimental-design
  metadata; retrieve mass-spectrometry-based protein quantitation matrices (log2-ratio / spectral
  counts); look up gene or protein spectral counts across studies; list files and obtain signed
  download URLs; map aliquots to cases; or run ad-hoc GraphQL queries against the PDC schema.
compatibility: Python 3 with the `requests` package. No API key, token, or login required — PDC is fully open-access.
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# Proteomic Data Commons (PDC) API

The NCI Proteomic Data Commons API is the programmatic interface behind
`proteomic.datacommons.cancer.gov`. It exposes harmonized, mass-spectrometry-based cancer proteomics
datasets (CPTAC, ICPC, APOLLO, and other programs) for search, retrieval, and download, plus the
protein quantitation matrices, spectral counts, and clinical/biospecimen metadata behind the PDC Data
Portal. As of this writing PDC holds ~9 programs, ~30 projects, ~227 studies, ~6,200 cases, and
~195k files (call `getPDCMetrics` for live totals).

**Endpoint:** `https://proteomic.datacommons.cancer.gov/graphql` — a **single GraphQL endpoint**.
There is no REST API; every operation is a GraphQL query against this one URL.

## Authentication

**None.** All PDC data and metadata are open-access — no API key, token, cookie, or login for any
query or download. (Web login exists only for data *submission*, which this API does not expose.)
See [auth.yaml](auth.yaml).

## Two ways to call it (GET vs POST)

PDC's GraphQL accepts the query string either way. The query is a single anonymous operation
`{ queryName(args) { fields } }`.

```python
import requests
URL = "https://proteomic.datacommons.cancer.gov/graphql"

# GET — fine for short queries; the query string is URL-encoded for you by requests' params=
requests.get(URL, params={"query": "{ getPDCMetrics { studies cases files data_size_TB } }"})

# POST — REQUIRED for large queries (deep `case`/`clinicalPerStudy` field sets blow past URL limits)
requests.post(URL, json={"query": "{ getPDCMetrics { studies cases files } }"})
```

Default to **POST** for anything beyond a one-line query. Responses are JSON: `{"data": {...}}` on
success, `{"errors": [...], "data": {...}}` on failure (PDC returns HTTP 200 even for query errors —
**always inspect `errors`**). See [references/QUERIES.md](references/QUERIES.md).

## Critical rules

- **Studies have three different IDs — and they are not interchangeable substitutes.** `pdc_study_id`
  (human-readable, **version-stable**, e.g. `PDC000127`); `study_id` (a UUID that is
  **version-specific** — it changes with each study version); `study_submitter_id` (a long name, e.g.
  `CPTAC CCRCC Discovery Study - Proteome S044-1`). Most per-study queries accept *any* of the three
  as a named argument, but each query documents one canonical arg, and a few only accept the one
  shown. Prefer `pdc_study_id` for stability; resolve the others via `studyCatalog` / `study`. See
  [references/ENTITIES.md](references/ENTITIES.md).
- **Pin the study version.** Because `study_id` is version-specific, a UUID can silently point at an
  old release. `studyCatalog` lists every `pdc_study_id`'s versions with `is_latest_version` — use
  the latest unless the user asks otherwise.
- **Paginated queries need `offset` AND `limit`, and the page is small.** The `getPaginated*` and
  `*PerStudy` queries require both; omit them and you get an error or a tiny default page, not the
  full set. `limit` cannot exceed **25000** (`fileMetadata`). Loop until a page returns fewer rows than
  `limit` — **don't trust `pagination.total`** (see next rule). See [references/PAGINATION.md](references/PAGINATION.md).
- **PDC returns transient `null` payloads under load — retry.** Intermittently a query comes back HTTP
  200 with `data: null`, or a populated result whose nested `pagination` is `null`, and **no `errors`**.
  It succeeds on retry. Wrap calls in a retry that re-requests when `data` (or a field you need) is
  null; never assume one call suffices. See [examples/quickstart.md](examples/quickstart.md).
- **`quantDataMatrix` returns the ENTIRE matrix in one call — no pagination.** For a proteome study
  this is genes × ~100-200 aliquots; the first call can be slow or time out (the result is then
  cached and fast on retry). It is **not** paginated, so you cannot cap it from the request — pick a
  smaller study or a sparser `data_type`. See [references/QUANTITATION.md](references/QUANTITATION.md).
- **PDC quantitation is RELATIVE, not absolute.** Values are log2 ratios against a common reference
  sample (isobaric TMT/iTRAQ workflows). There is no absolute protein abundance. Summary stats in the
  downloadable files are computed *before* median normalization. See QUANTITATION.md.
- **Spectral counts are per analytical sample, not per patient.** A TMT/iTRAQ analytical sample mixes
  several biological samples, so `geneSpectralCount` / `aliquotSpectralCount` reflect plex-level
  identification evidence, not per-case quantitation. Don't present them as per-patient values.
- **Download URLs expire and are rate-limited.** The `signedUrl { url }` on `filesPerStudy` is a
  pre-signed S3 link valid 7 days; the same file from the same IP is capped at 10 downloads/24h.
  Re-run the query for a fresh URL. See [references/FILES.md](references/FILES.md).
- **Don't invent fields or query names.** The schema is fixed (40 documented queries). An unknown
  field returns an `errors` block. Consult [references/QUERIES.md](references/QUERIES.md) or
  introspect the schema before guessing.

## Discovering studies (don't assume CPTAC-3 / a single study)

When the user names a disease, tissue, or cancer type rather than a `pdc_study_id`, enumerate the
matching studies first. Entry points: `diseasesAvailable`, `tissueSitesAvailable`,
`diseaseTypesPerProject`, `allExperimentTypes`, and `programsProjectsStudies(disease_type: ...)` (a
program→project→study hierarchy filtered by disease). Then run the real per-study query over the set.
See [references/DISCOVERY.md](references/DISCOVERY.md) and
[examples/discover_studies_for_disease.md](examples/discover_studies_for_disease.md).

## Query catalogue

All 40 queries, grouped. Full arguments, returned fields, and the canonical ID per query are in
[references/QUERIES.md](references/QUERIES.md).

| Group | Queries |
|---|---|
| Metrics & discovery | `getPDCMetrics`, `dataStatsPerProgram`, `diseasesAvailable`, `tissueSitesAvailable`, `diseaseTypesPerProject`, `allExperimentTypes`, `getPaginatedPublications` |
| Program / project | `allPrograms`, `program`, `programsProjectsStudies` |
| Study | `study`, `studyCatalog`, `studyExperimentalDesign`, `experimentalMetadata`, `protocolPerStudy`, `workflowMetadata`, `filesCountPerStudy` |
| Case / clinical / biospecimen | `allCases`, `case`, `getPaginatedCases`, `paginatedCasesSamplesAliquots`, `clinicalPerStudy`, `clinicalMetadata`, `paginatedCaseDemographicsPerStudy`, `paginatedCaseDiagnosesPerStudy`, `paginatedCaseExposuresPerStudy`, `paginatedCaseFollowUpsPerStudy`, `paginatedCaseTreatmentsPerStudy`, `biospecimenPerStudy` |
| Files | `fileMetadata`, `filesPerStudy`, `getPaginatedFiles` |
| Gene / protein / quantitation | `getPaginatedGenes`, `geneSpectralCount`, `aliquotSpectralCount`, `paginatedSpectralCountPerStudyAliquot`, `protein`, `quantDataMatrix` |
| Entity references | `reference`, `pdcEntityReference` |

## Argument syntax

Arguments are GraphQL named arguments inside the query, not a JSON `filters` document. Strings are
double-quoted; integers are bare:

```graphql
{ paginatedCaseDiagnosesPerStudy(study_id: "0fe15489-1381-4864-8b17-6159e14a65a8" offset: 0 limit: 100)
  { total caseDiagnosesPerStudy { case_submitter_id diagnoses { primary_diagnosis tumor_stage } }
    pagination { total pages size } } }
```

Many queries accept *more* filter arguments than their documented signature lists (e.g. `filesPerStudy`
also takes `file_type`, `data_category`, `file_format`). The extra accepted args are noted per query in
[references/QUERIES.md](references/QUERIES.md).

## Data model

`program → project → study → case → sample → aliquot → aliquot_run_metadata` (the labeled channel in a
plex). Files attach to studies; genes/proteins carry spectral counts spanning studies. Quant-matrix
columns are keyed `aliquot_id:aliquot_submitter_id`; map them back to cases via `biospecimenPerStudy`
or `paginatedCasesSamplesAliquots`. Full entity/field breakdown:
[references/ENTITIES.md](references/ENTITIES.md).

## Example usage

The smallest useful query — live repository totals, no auth:

```python
import requests
r = requests.post("https://proteomic.datacommons.cancer.gov/graphql",
                  json={"query": "{ getPDCMetrics { programs projects studies cases files data_size_TB } }"})
print(r.json()["data"]["getPDCMetrics"])
```

For complete worked examples see [examples/](examples/):

- [quickstart.md](examples/quickstart.md) — GET vs POST, error handling, the canonical request helper.
- [discover_studies_for_disease.md](examples/discover_studies_for_disease.md) — Disease/tissue → the studies that actually contain it (don't assume one study).
- [quant_matrix.md](examples/quant_matrix.md) — `quantDataMatrix` → a genes × aliquots DataFrame, with aliquot→case mapping.
- [study_files_download.md](examples/study_files_download.md) — List a study's files and fetch a signed download URL.
- [gene_spectral_counts.md](examples/gene_spectral_counts.md) — Gene/protein spectral counts across studies.
- [clinical_biospecimen.md](examples/clinical_biospecimen.md) — Pull per-study diagnoses + map aliquots to cases.
- [paginate_cases.md](examples/paginate_cases.md) — Loop `offset`/`limit` to retrieve a full result set.

## References

- [references/ENTITIES.md](references/ENTITIES.md) — Data model, the three study-ID flavors and how to
  resolve them, study versions, ID types per entity. Load before scoping a per-study query.
- [references/QUERIES.md](references/QUERIES.md) — All 40 queries: arguments (required + extra
  accepted), canonical ID, returned fields, notes. The endpoint catalogue.
- [references/PAGINATION.md](references/PAGINATION.md) — `offset`/`limit`, the 25000 cap, the
  `pagination` object, paginated vs bulk queries, loop patterns. Load when retrieving more than one page.
- [references/QUANTITATION.md](references/QUANTITATION.md) — `quantDataMatrix` shape and `data_type`
  values; log2-ratio vs unshared; spectral counts; common reference sample; normalization; why no
  absolute abundance. Load for any protein-expression task.
- [references/CLINICAL.md](references/CLINICAL.md) — Clinical/biospecimen queries, the deep `case`
  query, demographics/diagnoses/exposures/follow-ups/treatments split across queries.
- [references/FILES.md](references/FILES.md) — File metadata, data categories/types, `signedUrl`,
  download client, the 7-day expiry and 10/24h rate limit.
- [references/DISCOVERY.md](references/DISCOVERY.md) — Finding studies by disease, tissue, program, or
  experiment type; the discovery query set and the metrics queries.

The upstream Swagger spec (each query documented as a GET path) is preserved verbatim in
[assets/spec.json](assets/spec.json).
