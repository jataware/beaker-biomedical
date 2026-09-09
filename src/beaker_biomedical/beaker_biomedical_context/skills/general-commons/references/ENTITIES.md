# GC data model & identifiers

GC organizes everything under a fixed hierarchy. Knowing it tells you which query to call and how the
IDs chain together. Because GC is **data-type agnostic**, the part of the tree below `file`/`sample`
varies per study — a sequencing study populates `genomic_info`, an imaging study `images`, a
nanomaterials study `characterizations`/`compositions`, etc.

```
program ──< study ──< participant ──< { sample, diagnosis, treatment }
                 │                          └──< { pdx, characterization, publication, composition }
                 ├──< file ──< { genomic_info, proteomic, image, multiplex_microscopy, non_dicom* }
                 └──< { investigator, protocol, consent_group }
```

- A **program** (e.g. *Childhood Cancer Data Initiative*, *PDXNet*, *NCI Alliance for Nanotechnology*)
  contains **studies**.
- A **study** is a single dbGaP-registered submission, keyed by **`phs_accession`**. It declares its
  `study_data_types`, `study_access` (Open/Controlled), and counts.
- A **participant** (= patient/donor; the portal/UI calls it a *subject*) has **samples**
  (biospecimens), **diagnoses**, and **treatments**.
- **Files** attach to a study (and often to participants). Each file may carry one modality-specific
  metadata node: `genomic_info` (sequencing), `proteomic`, `image`, `multiplex_microscopy`, or a
  `non_dicom*` imaging node. See [DATA-TYPES.md](DATA-TYPES.md).

## `phs_accession` is the join key — and is required almost everywhere

`phs_accession` is the dbGaP study accession (e.g. `phs001287`). It ties every per-study record to its
study, and it is a **required argument** on `participants`, `samples`, `files`, `diagnoses`,
`treatments`, `genomic_info`, `images`, `proteomics`, `pdx`, the imaging-modality queries, the
study-extra queries, and every per-study `*Count`. Omitting it is a hard `MissingFieldArgument` error,
**not** an empty result.

**Resolve it first** via `studies` (the only query that lets you search by name/acronym):

```graphql
{ studies(study_acronyms: ["KF-ESGR"]) { phs_accession study_name study_acronym study_access } }
{ studies(study_names: ["CPTAC Pan-Cancer"]) { phs_accession study_acronym } }
{ studies(first: 100) { phs_accession study_name study_acronym study_data_types } }   # browse all
```

**Caveat:** most `phs_accession` values look like `phs######`, but a few GC studies use a different key
(e.g. caNanoLab's *caNanoLab Data* study reports `phs_accession: "10.17917"`, a DOI fragment). Always
read the real value from `studies` rather than assuming a `phs` prefix.

## Identifiers per entity

| Entity | Stable id field | Submitter/secondary id | Notes |
|---|---|---|---|
| program | `program_name` | `program_acronym`, `program_short_name` | `programs(program_names: [...])` |
| study | `phs_accession` | `study_id`, `study_acronym`, `study_name`, `crdc_id` | `study_id` ≠ `phs_accession` |
| participant | `participant_id` | `study_participant_id`, `dbGaP_subject_id` | UI calls it *subject* |
| sample | `sample_id` | `derived_from_specimen`, `biosample_accession` | links to `participant_id` |
| diagnosis | `diagnosis_id` | `study_diagnosis_id` | links to `participant_id` |
| treatment | `treatment_id` | — | links to `participant_id` |
| file | `file_id` (**DRS**, e.g. `dg.4DFC/<uuid>`) | `file_name`, `md5sum`, `crdc_id` | not an HTTP URL — see [FILES.md](FILES.md) |
| genomic_info | `genomic_info_id` | `library_id` | links to `file_id` |

`crdc_id` appears on most nodes and is the cross-CRDC identifier — a hook for joining a GC record to
the same entity in another commons.

## "participant" vs "subject"

The **Data Type Queries** use **`participant`** (`participants`, `participant_id`, `participantsCount`).
The **faceted-search** layer uses **`subject`** (`searchSubjects`, `subjectOverview`, `subjectDetail`,
`numberOfSubjects`, `samplesForSubjectId`). They refer to the **same entity** — two views, not two
datasets. Pick by task, not by preference:

- **Faceted search (`subject*`)** — the cohort-builder: filter across studies by characteristic and get
  facet counts. Start here when the user names a disease/trait rather than a study. See [SEARCH.md](SEARCH.md).
- **Data Type Queries (`participant*`)** — structured records of a known study by `phs_accession`
  (diagnoses, treatments, samples, files, sequencing/proteomic/imaging metadata).

A typical flow chains them: `searchSubjects` → resolve `phs_accession`(s) → Data Type Queries.

## Full field lists (verified live)

**Study** — `phs_accession study_id study_name study_acronym study_description short_description
study_external_url primary_investigator_name primary_investigator_email co_investigator_name
co_investigator_email bioproject_accession funding_agency funding_source_program_name grant_id
organism_species adult_or_childhood_study data_access_level number_of_participants number_of_samples
study_data_types file_types_and_format size_of_data_being_uploaded acl study_access authz study_version
role_or_affiliation title first_name middle_name last_name suffix email crdc_id`

**Program** — `program_name program_acronym program_short_description program_full_description
program_external_url program_short_name institution crdc_id`

**Participant** — `participant_id study_participant_id race sex ethnicity dbGaP_subject_id crdc_id
phs_accession`

**Sample** — `sample_id sample_type sample_description sample_type_category sample_tumor_status
sample_anatomic_site sample_age_at_collection derived_from_specimen biosample_accession
tumor_classification Organization_Name crdc_id phs_accession participant_id`

**Diagnosis** — `diagnosis_id study_diagnosis_id disease_type vital_status primary_diagnosis
primary_site age_at_diagnosis tumor_grade tumor_stage_clinical_m tumor_stage_clinical_n
tumor_stage_clinical_t morphology incidence_type progression_or_recurrence days_to_recurrence
days_to_last_followup last_known_disease_status days_to_last_known_status tissue_or_organ_of_origin
site_of_resection_or_biopsy days_to_last_known_disease_status crdc_id phs_accession participant_id`

**Treatment** — `treatment_id treatment_type days_to_treatment therapeutic_agents response crdc_id
phs_accession participant_id`

**File** — `file_id file_name file_type file_description file_size md5sum file_url_in_cds
experimental_strategy_and_data_subtypes submission_version checksum_value checksum_algorithm crdc_id
file_mapping_level release_datetime is_supplementary_file phs_accession participant_ids`

**Version** — `data_version_id data_version datetime model_version description crdc_id`

All values are returned as **String** (cast numbers/sizes yourself). Modality node fields are in
[DATA-TYPES.md](DATA-TYPES.md).
