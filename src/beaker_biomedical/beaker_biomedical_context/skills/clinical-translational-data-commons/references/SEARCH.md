# Faceted search & cohort building

CTDC's Elasticsearch-backed **faceted search** — `searchParticipants` + the `*Overview` row queries —
is the way to build a cohort by characteristic (the portal's Explore page). Defined in the schema
[../assets/ctdc-graphql-schema.graphql](../assets/ctdc-graphql-schema.graphql); the underlying ES
indices (`widgets_facets_counts`, `tab_participants`, `tab_biospecimens`, `tab_data_files`) are in
[../assets/es-indices-ctdc.yml](../assets/es-indices-ctdc.yml).

## The shared facet arguments

`searchParticipants`, `participantOverview`, `biospecimenOverview`, and `fileOverview` share this filter
set. Each is a **list** (`[String]`, default `[]` = no constraint); values within a facet OR, different
facets AND.

| Group | Facet args |
|---|---|
| Study | `study_short_name` |
| Diagnosis | `ctep_disease_term`, `primary_diagnosis_disease_group`, `stage_of_disease`, `tumor_grade` |
| Demographic | `sex`, `race`, `ethnicity` |
| Exposure / therapy | `carcinogen_exposure`, `targeted_therapy`, `targeted_therapy_string` |
| Specimen | `anatomical_collection_site`, `specimen_type`, `tissue_category`, `assessment_timepoint` |
| File | `data_file_type`, `data_file_format`, `association` |
| IDs | `participant_id` (+ `specimen_id` on specimen/file queries, `data_file_uuid` on file queries) |

The `*Overview` queries add `order_by`, `sort_direction` (`ASC`/`DESC`), `first` (**default 10**),
`offset`.

**Values are controlled vocabularies** — get them from `searchParticipants` facet counts, don't
hardcode. Live examples (CMB study): `ctep_disease_term` → `Plasma Cell Myeloma` (64),
`Non-Small Cell Lung Carcinoma` (52), `Colorectal Carcinoma` (50), `Melanoma` (45); `specimen_type` →
`Streck Blood to VARI`, `EDTA Blood`, `FFPE Block`; `sex` → `Male`, `Female`.

## `searchParticipants` → SearchResult (counts + facet counts, NOT rows)

Returns the summary for the current filter; it does **not** return record rows (use the `*Overview`
queries for those). Three groups of fields:

1. **Counts for the filter:** `numberOfStudies`, `numberOfParticipants`, `numberOfDiagnoses`,
   `numberOfTargetedTherapies`, `numberOfSpecimens`, `numberOfFiles`.
2. **Per-facet group counts** — every bucket is `GroupCount { group subjects }` (count field is
   **`subjects`**, not `count`). Two parallel families:
   - `participantCountBy<Facet>` / `specimenCountBy<Facet>` / `dataFileCountBy<Facet>` — counts over the
     **whole repository** (unfiltered landscape): `participantCountByCtepDiseaseTerm`,
     `participantCountByPrimaryDiagnosisDiseaseGroup`, `participantCountByStageOfDisease`,
     `participantCountByTumorGrade`, `participantCountBySex`, `participantCountByRace`,
     `participantCountByEthnicity`, `participantCountByCarcinogenExposure`,
     `participantCountByTargetedTherapy`, `participantCountBySingleTargetedTherapyCombination`,
     `participantCountBySnomedDiseaseCode`, `participantCountByAssessmentTimepoint`;
     `specimenCountByAnatomicalCollectionSite`, `specimenCountByTissueCategory`,
     `specimenCountBySpecimenType`; `dataFileCountByDataFileType`, `dataFileCountByDataFileFormat`.
   - `filterParticipantCountBy<Facet>` / `filterSpecimenCountBy<Facet>` / `filterDataFileCountBy<Facet>`
     — the same dimensions but counted **after the current filter** (what the portal shows to refine).
3. **Combined facets** (paired dimensions for the dashboard): `diagnosesAndStageOfDiseases`,
   `racesAndEthnicities`, `timepointsAndBiospecimensTypes`.

> Specimen/file buckets count **specimens/files**, not participants — they sum above the participant
> total because one participant has many specimens.

```graphql
{ searchParticipants(ctep_disease_term: ["Plasma Cell Myeloma"]) {
    numberOfParticipants numberOfSpecimens numberOfFiles
    filterParticipantCountBySex { group subjects }
    filterParticipantCountByTargetedTherapy { group subjects }
    filterSpecimenCountBySpecimenType { group subjects } } }
```

## Row queries (`participantOverview` / `biospecimenOverview` / `fileOverview`)

Same facet args, plus paging; **default `first: 10`** — set it and loop `offset` for the full set (see
[../examples/faceted_search.md](../examples/faceted_search.md)).

- `participantOverview` → `ParticipantOverview`: `participant_id`, `study_short_name`,
  `ctep_disease_term`, `primary_diagnosis_disease_group`, `primary_disease_site`, `stage_of_disease`,
  `tumor_grade`, `age_at_enrollment`, `sex`, `race`, `ethnicity`, `carcinogen_exposure`,
  `targeted_therapy`, `specimen_id`, `anatomical_collection_site`, `tissue_category`,
  `assessment_timepoint`, `surgical_procedure*`, `data_files`, …
- `biospecimenOverview` → `BiospecimenOverview`: `specimen_id`, `specimen_record_id`,
  `anatomical_collection_site`, `specimen_type`, `tissue_category`, `assessment_timepoint`,
  `participant_id`, `ctep_disease_term`, `data_file_uuid`, `data_files`, …
- `fileOverview` → `FileOverview`: `data_file_name`, `data_file_type`, `data_file_format`,
  `data_file_size`, `data_file_uuid`, **`drs_uri`**, `data_file_location`, `data_file_checksum_value`,
  `participant_id`, `specimen_id`, `association`, `study_short_name`, … See [FILES.md](FILES.md).

> Multi-valued `*Overview` fields are returned as **bracketed strings**, not arrays:
> `targeted_therapy: "[Lenalidomide, Bortezomib]"`, `tissue_category: "[, Primary]"`. Parse yourself.

## `globalSearch` (free text)

`globalSearch(input: "...", first: 10, offset: 0)` → `participants`/`participant_count`,
`biospecimens`/`biospecimen_count`, `about_page`/`about_count`, `model`/`model_count`, plus `gs_list`
and `model_search`. Good first move when a term could be a disease, therapy, or model property.

## Picking the right tool

- "How many participants of X, by sex/therapy/specimen?" → `searchParticipants` facet counts.
- "List the participants/specimens/files matching X" → `participantOverview`/`biospecimenOverview`/`fileOverview`.
- "Structured longitudinal records for a study" → `clinicalData` / `clinicalTrialData` ([CLINICAL.md](CLINICAL.md)).
- "Is this term in CTDC?" → `globalSearch`.
