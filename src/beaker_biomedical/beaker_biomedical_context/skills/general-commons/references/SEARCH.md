# Faceted search & cohort building (Bento ES layer)

GC's GraphQL has **two query families**. This file covers the **Bento Elasticsearch-backed faceted
search** — `searchSubjects` + the `*Overview` row queries — which is the primary interface for building
a cohort by characteristics (the portal's Explore page). The other family, the Gen3-style **Data Type
Queries** (`participants`, `diagnoses`, `treatments`, `files`, …) for structured per-study record pulls,
is in [QUERIES.md](QUERIES.md). The faceted layer is defined in the backend schema
[../assets/general-commons-schema.graphql](../assets/general-commons-schema.graphql); the underlying ES
indices are [../assets/es-indices.yaml](../assets/es-indices.yaml).

> **Terminology:** in this ES layer the entity is the **subject** (`searchSubjects`, `numberOfSubjects`,
> `subjectOverview`). A "subject" is the same thing the Data Type Queries call a **participant**. The
> two layers are different *views* of the same data, not different data.

## The shared facet arguments

`searchSubjects`, `subjectOverview`, `sampleOverview`, `fileOverview`, and `protocolOverview` all take
the same large filter set. Each facet is a **list** (`[String]`, default `[]` = no constraint); values
within a facet are OR'd, different facets are AND'd. The dimensions:

| Group | Facet args |
|---|---|
| Study | `studies`, `phs_accession`, `study_data_types`, `accesses`, `acl`, `site` |
| Subject | `sex`, `primary_diagnoses` |
| Sample | `sample_types`, `is_tumor`, `organ_or_tissue` |
| File | `file_types`, `experimental_strategies`, `is_supplementary_file` |
| Sequencing | `library_strategies`, `library_layouts`, `library_selections`, `library_source_materials`, `library_source_molecules`, `platforms`, `instrument_models`, `reference_genome_assemblies` |
| Imaging | `image_modality`, `imaging_assay_type` |
| Proteomics | `analytical_fractions`, `instrument_makes`, `proteomic_design_descriptions`, `tissue_fixative` |
| Protocol / publication | `protocol_names`, `protocol_types`, `dois`, `publication_titles`, `publication_statuses`, `pub_ids` |
| caNanoLab composition / characterization | `nanomaterial_entities`, `functionalizing_entities`, `characterization_types`, `characterization_names` |
| Range (numeric) | `number_of_study_participants` ([Float]), `number_of_study_samples` ([Float]) |
| IDs | `subject_ids` (+ `sample_ids` on sample/file, `file_ids` on file) |

**Values are controlled vocabularies** — get them from `searchSubjects` facet counts, don't hardcode.
A wrong value yields an empty result with no error.

## `searchSubjects` → SearchResult (counts + facet counts, NOT rows)

`searchSubjects` returns the summary for the current filter; it does **not** return record rows (use the
`*Overview` queries for those). It returns three things:

1. **Counts for the filter:** `numberOfStudies`, `numberOfSubjects`, `numberOfSamples`,
   `numberOfFiles`, `numberOfDiseaseSites`, `numberOfProtocols`.
2. **Per-facet group counts**, two parallel families — note each bucket's count field is **`subjects`**
   (not `count`):
   - `subjectCountBy<Facet>` — counts over the **whole repository** (the unfiltered landscape):
     `subjectCountByStudy`, `subjectCountByPhsAccession`, `subjectCountBySex`,
     `subjectCountByPrimaryDiagnosis`, `subjectCountByExperimentalStrategy`, `subjectCountByFileType`,
     `subjectCountBySampleType`, `subjectCountByIsTumor`, `subjectCountByStudyDataType`,
     `subjectCountByAccess`, `subjectCountByDiseaseSite`, `subjectCountByLibraryStrategy`,
     `subjectCountByPlatform`, `subjectCountByImageModality`, `subjectCountByInstrumentModel`,
     `subjectCountByAnalyticalFractions`, … (39 dimensions; full list in the schema).
   - `filterSubjectCountBy<Facet>` — counts **after the current filter** (what the portal shows to
     refine). Two of these are ranges, not groups: `filterSubjectCountByNumberOfStudyParticipants`
     and `filterSubjectCountByNumberOfStudySamples` return `RangeCount { lowerBound upperBound subjects }`.
3. **Donut chart counts** (a small curated subset for the dashboard): `donutCountByExperimentalStrategy`,
   `donutCountBySex`, `donutCountByFileType`, `donutCountByStudyDataTypes`, `donutCountByImageModality`,
   `donutCountBySampleType`.

`GroupCount` is `{ group: String, subjects: Int }`.

```graphql
{ searchSubjects(primary_diagnoses: ["Glioblastoma, NOS"], sex: ["Female"]) {
    numberOfStudies numberOfSubjects numberOfSamples numberOfFiles
    filterSubjectCountByPhsAccession { group subjects }
    filterSubjectCountByExperimentalStrategy { group subjects } } }
```

## Row queries (`subjectOverview` / `sampleOverview` / `fileOverview` / `protocolOverview`)

Same facet args, plus `order_by`, `sort_direction` (`ASC`/`DESC`), `first` (**default 10**), `offset`.
They return flat rows; loop `offset` for the full set (see [PAGINATION.md](PAGINATION.md)).

- `subjectOverview` → `SubjectOverview`: `subject_id`, `study_participant_id`, `study_acronym`,
  `phs_accession`, `sex`, `site`, `race`, `ethnicity`, `primary_diagnosis`, `samples`, `files`
  (the `files` are CRDC **DRS ids** like `dg.4DFC/<uuid>`).
- `sampleOverview` → `SampleOverview`: `sample_id`, `sample_type`, `is_tumor`, `analyte_type`,
  `organ_or_tissue`, `subject_id`, `phs_accession`, `files`, …
- `fileOverview` → `FileOverview`: `file_id`, `file_name`, `file_type`, `file_size`, `md5sum`,
  `experimental_strategy`, `accesses`, `phs_accession`, `subject_id`, `sample_id`, `image_modality`, …
- `protocolOverview` → `ProtocolOverview`: `protocol_pk_id`, `protocol_name`, `protocol_type`, `doi`,
  `doi_url`, `file_names`.

```graphql
{ subjectOverview(primary_diagnoses: ["Glioblastoma, NOS"], first: 50, offset: 0,
                  order_by: "subject_id", sort_direction: "ASC") {
    subject_id phs_accession sex primary_diagnosis samples files } }
```

## Manifest / download helpers

- `filesInList(...)` → `[FilesInList]` — like `fileOverview` but includes **`drs_uri`** (a
  `drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>` link) plus `accesses` and the `associated_*` fields
  (index/sidecar files). Use this to assemble a download manifest. See [FILES.md](FILES.md).
- `fileIDsFromList(subject_ids, sample_ids, file_names, file_ids, study_participant_ids,
  protocol_pk_ids)` → `[String]` — resolve a mix of ids to file ids.
- `idsLists` → `{ subjectIds }`; `findSubjectIdsInList(subject_ids)` → `[SubjectResult]`.

## Picking the right family

- "How many subjects/files of X, and what studies/strategies cover it?" → `searchSubjects` facet counts.
- "List the subjects/samples/files matching X (across studies)" → `subjectOverview`/`sampleOverview`/`fileOverview`.
- "Give me the structured clinical/biospecimen records for one study" → Data Type Queries with
  `phs_accession` ([QUERIES.md](QUERIES.md)).
- "Is this term in GC at all?" → `globalSearch` ([DISCOVERY.md](DISCOVERY.md)).
