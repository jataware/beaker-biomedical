---
name: clinical-translational-data-commons
description: >-
  Query, search, and build cohorts from the NCI Clinical and Translational Data Commons (CTDC) GraphQL
  API — a Cancer Research Data Commons (CRDC) repository of clinical-trial and translational data
  (CTEP-coded diagnoses, targeted/non-targeted therapy, surgery, radiotherapy, carcinogen exposure)
  with linked biospecimens and data files. Use when the user needs to find CTDC studies (e.g. the CM
  Biobank); build a participant cohort by CTEP disease term, disease group, stage, tumor grade, sex,
  race/ethnicity, carcinogen exposure, targeted therapy, specimen type, anatomical collection site,
  timepoint, or file type/format; pull per-participant clinical, demographic, diagnosis, exposure,
  treatment, or specimen records; retrieve a study's longitudinal clinical / clinical-trial node data;
  list biospecimens or data files and get their CRDC DRS ids for download; or run ad-hoc GraphQL
  against the CTDC schema. NOT for: imaging pixels (use the imaging-data-commons), genomics (GDC),
  proteomics (PDC), or general CDS studies (general-commons).
compatibility: Python 3 with the `requests` package. No API key, token, or login required — CTDC metadata/search is open-access. The API serves metadata/search only; file bytes are downloaded out-of-band via CRDC DRS / the Cancer Genomics Cloud.
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# Clinical and Translational Data Commons (CTDC) API

The NCI **Clinical and Translational Data Commons** is a Cancer Research Data Commons (CRDC) repository
for **clinical-trial and translational research** data: participants with CTEP-coded diagnoses, their
treatments (targeted therapy, non-targeted therapy, surgery, radiotherapy), exposures, outcomes, and
linked biospecimens and data files. Its GraphQL API is the programmatic interface behind
`clinical.datacommons.cancer.gov`. It is a **Bento-framework** commons (like General Commons and the
Integrated Canine Data Commons). As of this writing CTDC is **early/small — 1 study (CMB, the "CM
Biobank"), 248 participants, ~1,140 specimens, ~2,033 files, 42 targeted therapies** (call
`searchParticipants` for live totals).

**Endpoint:** `https://clinical.datacommons.cancer.gov/v1/graphql/` — a **single GraphQL endpoint,
POST-only**. There is no REST API.

## Authentication

**None.** All CTDC metadata and search is open-access — no API key, token, cookie, or login. See
[auth.yaml](auth.yaml). The API returns metadata only; it does not stream file bytes. Files carry a
CRDC **DRS** id (`dg.4DFC/<uuid>`) you resolve out-of-band (DRS / Cancer Genomics Cloud). See
[references/FILES.md](references/FILES.md).

## Calling it (read this — two non-obvious request rules)

```python
import requests
URL = "https://clinical.datacommons.cancer.gov/v1/graphql/"   # trailing slash; POST only
requests.post(URL, json={"query": "{ getAllStudies { study_short_name participant_count } }",
                         "variables": {}})                     # variables key is REQUIRED
```

- **POST only.** A GET is rejected (`{"errors":[{"message":"API will only accept POST requests"}]}`).
- **The request body MUST include a `variables` key** (even `{}`). Omitting it is a hard error
  (`Cannot invoke "java.util.Map.keySet()" because "variables" is null`), *not* an empty result. This
  is a CTDC quirk — its sibling Bento commons don't require it.
- Responses are JSON; **HTTP 200 even on query errors** — always inspect `errors`.
- **Use the Elasticsearch-backed queries.** `schemaVersion` (the one neo4j-backed query) currently
  errors on the public endpoint; every other query is ES-backed and works.

See [examples/quickstart.md](examples/quickstart.md).

## Two query families (pick the right one)

CTDC exposes ~18 working queries in two families — see [references/QUERIES.md](references/QUERIES.md):

1. **Faceted search (Elasticsearch-backed)** — the cohort-builder, centered on the **participant**.
   `searchParticipants` returns repository counts **and** per-facet group counts across ~16 dimensions
   (CTEP disease term, disease group, stage, tumor grade, sex, race, ethnicity, carcinogen exposure,
   targeted therapy, specimen type, anatomical site, tissue category, timepoint, file type/format);
   `participantOverview` / `biospecimenOverview` / `fileOverview` return the matching paged rows;
   `filesInList` builds a download list with DRS URIs. See [references/SEARCH.md](references/SEARCH.md).
2. **Per-study queries** — `getAllStudies`, `studyByStudyShortName`, `studyDiagnosisByStudyShortName`,
   `StudySpecimenByStudyShortName`, `StudyDataFileByStudyShortName`, and the longitudinal
   `clinicalData` / `clinicalTrialData` node-data queries. See [references/CLINICAL.md](references/CLINICAL.md).

Plus `globalSearch` (free-text) and `getHomePage` / `getInteropData` (portal widgets).

## Critical rules

- **POST + `variables` key required; HTTP 200 on errors.** See "Calling it" above — these are the three
  ways a first call most often fails.
- **In the faceted layer, each facet bucket's count field is `subjects`, not `count`** (`GroupCount {
  group subjects }`) — even though the entity is the "participant." Asking for `count` is a
  `FieldUndefined` error. (The per-study `SpecimenType`/`SpecimenTimepoint` summaries *do* use `count`.)
- **Multi-valued fields come back as bracketed STRINGS, not JSON arrays.** On the `*Overview` rows,
  `targeted_therapy` → `"[Lenalidomide, Bortezomib]"`, `anatomical_collection_site` → `"[Blood, Iliac
  Crest]"`, `tissue_category` → `"[, Primary]"`. Parse them yourself; don't expect a list.
- **Facet values are controlled vocabularies — an empty result usually means a wrong value, not absent
  data.** CTEP disease terms (`Plasma Cell Myeloma`, `Non-Small Cell Lung Carcinoma`, …), specimen
  types (`EDTA Blood`, `FFPE Block`, …), etc. are exact strings. Discover valid values from
  `searchParticipants` facet counts first; don't hardcode a guess.
- **Specimen/file facet counts are per-specimen/per-file, not per-participant.** A participant has many
  specimens, so e.g. `specimenCountBySpecimenType` sums above the participant total — don't read those
  buckets as patient counts.
- **The API never downloads bytes.** Files expose a DRS id (`dg.4DFC/<uuid>` →
  `drs://nci-crdc.datacommons.io/...`); `data_file_location` is often null. Resolve via CRDC DRS or the
  Cancer Genomics Cloud. See [references/FILES.md](references/FILES.md).
- **Don't invent fields or query names.** The schema is fixed (19 queries). Unknown fields return a
  `Validation error (FieldUndefined)`. Catalogue: [assets/query-fields.txt](assets/query-fields.txt) +
  [references/QUERIES.md](references/QUERIES.md); introspect with
  `{ __type(name:"ParticipantOverview"){ fields { name } } }` (remember the `variables` key).

## Building a cohort (the common task)

When the user names a cancer, therapy, or specimen trait, start at `searchParticipants` to see the
facet landscape (which CTEP terms / therapies / specimen types exist and their counts), narrow with the
facet arguments, then pull rows with `participantOverview` / `biospecimenOverview` / `fileOverview`. See
[examples/faceted_search.md](examples/faceted_search.md).

## Data model

```
Study ──< Participant ──< { demographic(1), participant_status(1),
                            exposure[], diagnosis[], specimens[],
                            targeted_therapy[], non_targeted_therapy[], surgery[], radiotherapy[] }
DataFile attaches to participant / specimen (and study level); each carries a DRS id.
```

`study_short_name` (e.g. `CMB`) joins per-study records; `participant_id` (e.g. `MSB-00089`) joins
per-participant records; `specimen_id` and `data_file_uuid` key specimens and files. The clinical-trial
treatment nodes (targeted/non-targeted therapy, surgery, radiotherapy) plus CTEP/SNOMED/MedDRA-coded
diagnoses are what distinguish CTDC. Full node/field breakdown: [references/ENTITIES.md](references/ENTITIES.md).

## Example usage

The smallest useful query — live totals for the current study set, no auth:

```python
import requests
r = requests.post("https://clinical.datacommons.cancer.gov/v1/graphql/",
                  json={"query": "{ searchParticipants { numberOfStudies numberOfParticipants "
                                 "numberOfSpecimens numberOfFiles numberOfTargetedTherapies } }",
                        "variables": {}})
print(r.json()["data"]["searchParticipants"])
# {'numberOfStudies': 1, 'numberOfParticipants': 248, 'numberOfSpecimens': 1140,
#  'numberOfFiles': 2033, 'numberOfTargetedTherapies': 42}
```

For complete worked examples see [examples/](examples/):

- [quickstart.md](examples/quickstart.md) — the POST helper (with `variables`), error handling, totals.
- [discover_studies.md](examples/discover_studies.md) — `getAllStudies`, `studyByStudyShortName`, `globalSearch`.
- [faceted_search.md](examples/faceted_search.md) — `searchParticipants` facets → cohort → `participantOverview` rows.
- [clinical_data.md](examples/clinical_data.md) — per-study `clinicalData` / `clinicalTrialData` node tables.
- [files_and_download.md](examples/files_and_download.md) — biospecimen/file rows → DRS id → CGC.

## References

- [references/QUERIES.md](references/QUERIES.md) — the 19 queries grouped by family: arguments, return
  types, which to use when, the broken/portal ones. The endpoint catalogue.
- [references/SEARCH.md](references/SEARCH.md) — `searchParticipants` (the ~16 facet dimensions,
  `participantCountBy*` vs `filterParticipantCountBy*`, the combined facets), the `*Overview` row
  queries, `GroupCount.subjects`. Load for any cohort/discovery task.
- [references/ENTITIES.md](references/ENTITIES.md) — data model, every node + its fields, the ID keys,
  the bracketed-string array quirk. Load before scoping a per-entity pull.
- [references/CLINICAL.md](references/CLINICAL.md) — per-study `clinicalData` (diagnosis / demographic /
  exposure / specimen / participant-status) and `clinicalTrialData` (targeted / non-targeted therapy /
  radiotherapy / surgery) node-data queries.
- [references/FILES.md](references/FILES.md) — file records, the DRS `dg.4DFC/` id / `drs_uri`, open
  access, the Cancer Genomics Cloud workflow, why the API never downloads.

Upstream specs are preserved verbatim in [assets/](assets/): `ctdc-graphql-schema.graphql` (the ES
GraphQL schema — the authoritative API surface), `es-indices-ctdc.yml` (the Elasticsearch index
definitions behind the faceted search), and `query-fields.txt` (the full introspected query list).
