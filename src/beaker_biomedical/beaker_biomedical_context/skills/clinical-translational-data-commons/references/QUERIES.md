# CTDC query catalogue

Single endpoint: `POST https://clinical.datacommons.cancer.gov/v1/graphql/` with body
`{"query": "...", "variables": {}}` — **the `variables` key is required** (even empty), and **GET is
rejected**. CTDC returns HTTP 200 even on query errors — inspect the `errors` array. Arguments are
GraphQL named args (strings double-quoted, ints bare, lists in `[...]`).

The full introspected list (19 fields) is [../assets/query-fields.txt](../assets/query-fields.txt); the
authoritative schema is [../assets/ctdc-graphql-schema.graphql](../assets/ctdc-graphql-schema.graphql).
**18 of the 19 are Elasticsearch-backed and work; `schemaVersion` (the lone neo4j-backed query)
currently errors** on the public endpoint.

---

## 1. Faceted search (Elasticsearch) — the cohort-builder → [SEARCH.md](SEARCH.md)

Centered on the **participant**. The first four share a ~16-dimension facet arg set (each a list;
OR within a facet, AND across facets) — full facet list + return shapes in [SEARCH.md](SEARCH.md).

| Query | Args | Returns | Use |
|---|---|---|---|
| `searchParticipants` | the facet args | `SearchResult` | Counts + per-facet group counts (`GroupCount { group subjects }`). **Not paged; returns counts, not rows.** |
| `participantOverview` | facet args + `order_by`,`sort_direction`,`first`,`offset` | `[ParticipantOverview]` | Paged participant rows. |
| `biospecimenOverview` | facet args (+`specimen_id`,`data_file_uuid`) + paging | `[BiospecimenOverview]` | Paged specimen rows. |
| `fileOverview` | facet args (+`specimen_id`,`specimen_record_id`,`data_file_uuid`,`drs_uri`) + paging | `[FileOverview]` | Paged file rows (incl. `drs_uri`). |
| `participant_data_files` | facet args + paging | `[FileParticipant]` | Files joined at participant level. |
| `biospecimen_data_files` | facet args (+`specimen_id`,`specimen_record_id`) + paging | `[FileOverview]` | Files joined at specimen level. |
| `filesInList` | `data_file_uuid: [String]` + `order_by`,`sort_direction`,`first`,`offset` | `[FileOverview]` | File rows for an explicit uuid list — build a manifest ([FILES.md](FILES.md)). |
| `fileIDsFromList` | `participant_id`, `specimen_id`, `data_file_uuid`, `data_file_name` (each [String]) | `[String]` | Resolve mixed ids → file uuids. |

> Faceted bucket counts use the field name **`subjects`**, not `count`.

## 2. Per-study queries

| Query | Args | Returns | Notes |
|---|---|---|---|
| `getAllStudies` | — | `[Study]` | Every study with counts (`participant_count`, `study_file_count`, `participant_file_count`, `image_collection_count`) + PIs, publications, consent groups, image collections. |
| `studyByStudyShortName` | `study_short_name`, `study_id` | `[Study]` | One study's full record. |
| `studyDiagnosisByStudyShortName` | `study_short_name`, `study_id` | `[StudyDiagnosis]` | A study's diagnoses + `ctep_disease_terms`. |
| `StudySpecimenByStudyShortName` | `study_short_name`, `study_id` | `[StudySpecimen]` | A study's specimen types/timepoints + `specimen_count` (note capital `S`). |
| `StudyDataFileByStudyShortName` | `study_short_name`, `study_id` | `[StudyDataFile]` | A study's study-level + participant data files (note capital `S`). |
| `clinicalData` | `study_short_name`, `study_id` | `[ClinicalData]` | Per-study longitudinal node data: diagnosis / demographic / exposure / specimen / participant-status (+ node & participant counts). See [CLINICAL.md](CLINICAL.md). |
| `clinicalTrialData` | `study_short_name`, `study_id` | `[ClinicalTrialData]` | Per-study treatment node data: targeted / non-targeted therapy / radiotherapy / surgery (+ counts). See [CLINICAL.md](CLINICAL.md). |

## 3. Free-text & portal

| Query | Args | Returns | Notes |
|---|---|---|---|
| `globalSearch` | `input`, `first`, `offset`, `order_by`, `sort_direction`, `participant_id` | `GlobalSearchResult` | Free-text → `participants`/`participant_count`, `biospecimens`/`biospecimen_count`, `about_page`/`about_count`, `model`/`model_count`, `gs_list`, `model_search`. |
| `getHomePage` | — | `[HomePage]` | Portal landing-page widget data. |
| `getInteropData` | — | `[Interop]` | Cross-CRDC interoperation links (e.g. to IDC/TCIA for imaging). |
| `schemaVersion` | — | `String` | **Currently errors** (neo4j-backed, store unreachable on the public endpoint). |

## ID keys

| Entity | Key | Example |
|---|---|---|
| study | `study_short_name` (also `study_id`) | `CMB` |
| participant | `participant_id` | `MSB-00089` |
| specimen | `specimen_id` / `specimen_record_id` | — |
| file | `data_file_uuid` (= DRS `dg.4DFC/<uuid>`) | `dg.4DFC/e2cf5d14-…` |

## Resolving the schema at runtime

Remember the `variables` key on every call:

```json
{"query": "{ __type(name: \"ParticipantOverview\") { fields { name } } }", "variables": {}}
{"query": "{ __schema { queryType { fields { name } } } }", "variables": {}}
```
