# CTDC data model & entities

CTDC is a Bento commons (Neo4j graph surfaced through GraphQL, with Elasticsearch indices behind the
faceted search). The data model is centered on the **participant** and their clinical-trial /
translational records. Full schema: [../assets/ctdc-graphql-schema.graphql](../assets/ctdc-graphql-schema.graphql).

## Graph structure

```
Study ──< Participant ──< demographic            (1 per participant)
                       ├─< participant_status     (1: survival_status, off_study, cause_of_death)
                       ├─< diagnosis []           (CTEP/SNOMED/MedDRA-coded)
                       ├─< exposure []            (carcinogen / environmental exposure)
                       ├─< specimens []           (biospecimens)
                       ├─< targeted_therapy []        ┐
                       ├─< non_targeted_therapy []    │  clinical-trial treatment modalities
                       ├─< surgery []                 │
                       └─< radiotherapy []            ┘
DataFile attaches to a participant and/or specimen (and at study level); each carries a CRDC DRS id.
```

`study_short_name` joins per-study records; `participant_id` joins per-participant records. The
treatment nodes + CTEP-coded diagnoses are what make CTDC a *clinical-trial / translational* commons.

## ID keys

| Entity | Key argument | Example |
|---|---|---|
| study | `study_short_name` (also `study_id`) | `CMB` |
| participant | `participant_id` | `MSB-00089` |
| specimen | `specimen_id` / `specimen_record_id` | — |
| file | `data_file_uuid` (= DRS id `dg.4DFC/<uuid>`) | `dg.4DFC/e2cf5d14-…` |

A wrong/misspelled value usually yields an **empty list, not an error**.

## Studies (live)

CTDC currently holds **1 study**: `CMB` — "CM Biobank" (Observational Study), 248 participants, ~1,140
specimens, ~2,033 files. Call `getAllStudies` for the current set; expect it to grow.

## Nodes and their key fields

Use `{ __type(name:"<Type>"){ fields { name } } }` (with the `variables` key) for the exhaustive list.

- **Study** — `study_short_name`, `study_accession`, `study_id`, `study_name`, `study_description`,
  `study_type` (e.g. `Observational Study`), `dates_of_conduct`, `participant_count`,
  `study_file_count`, `participant_file_count`, `image_collection_count`; nested `participants`,
  `principal_investigators`, `publications`, `consent_groups`, `associated_links`, `image_collection`.
- **Participant** — `participant_id`, `study_short_name`, `*_available` flags
  (`biomarker_results_available`, `histology_images_available`, `radiology_images_available`,
  `radiology_report_available`); nested `demographic`, `participant_status`, `diagnosis[]`,
  `exposure[]`, `specimens[]`, `targeted_therapy[]`, `non_targeted_therapy[]`, `surgery[]`,
  `radiotherapy[]`.
- **Demographic** — `age_at_enrollment` (Float), `sex`, `race`, `ethnicity`, `height`, `weight`,
  `body_surface_area`, `occupation`, `income`, `highest_level_of_education`, `ncbi_taxonomy_name`.
- **Diagnosis** — `ctep_disease_term`, `primary_diagnosis_disease_group`, `meddra_disease_code`,
  `snomed_disease_term`, `snomed_disease_code`, `primary_disease_site`, `histology`,
  `histological_subtype`, `stage_of_disease`, `tumor_grade`.
- **Exposure** — `environmental_exposure_type`, `carcinogen_exposure`.
- **TargetedTherapy** — `targeted_therapy`, `targeted_therapy_dose`(+`_units`), `*_frequency`,
  `*_start_date`/`*_end_date`, `best_response_to_targeted_therapy`. (NonTargetedTherapy mirrors it.)
- **Surgery** — `surgical_procedure`, `surgical_procedure_date`, `surgical_procedure_anatomical_location`,
  `surgical_procedure_therapeutic`, `surgical_procedure_findings`, `extent_of_residual_disease`.
- **Radiotherapy** — `radiological_procedure`, `radiological_procedure_anatomical_location`,
  `radiation_dose`(+`_units`), `radiation_frequency`, `radiation_extent`, `radiotherapy_start/end_date`,
  `best_response_to_radiotherapy`.
- **ParticipantStatus** — `survival_status`, `primary_cause_of_death`, `off_study`, `off_study_reason`.
- **Specimen** — `specimen_record_id`, `specimen_type`, `specimen_category`,
  `anatomical_collection_site`, `tissue_category`, `assessment_timepoint`, `collection_date`.
- **DataFile** — `data_file_uuid`, `data_file_name`, `data_file_type` (e.g. `Radiology Imaging`),
  `data_file_format` (`DICOM`, …), `data_file_size` (Float), `data_file_checksum_value`(+`_type`),
  `data_file_compression_status`, `data_file_location`. DRS id / `drs_uri` come via the `*Overview`
  queries (see [FILES.md](FILES.md)).

## The bracketed-string array quirk

The flattened `*Overview` rows return multi-valued fields as **bracketed strings, not JSON arrays** —
e.g. `targeted_therapy: "[Lenalidomide, Bortezomib]"`, `anatomical_collection_site: "[Blood, Iliac
Crest]"`, `tissue_category: "[, Primary]"` (note empty leading element). Parse the string yourself;
don't index it as a list. The nested node queries (e.g. `Participant.targeted_therapy`) return proper
typed objects instead.
