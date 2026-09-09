# GC query catalogue

Single endpoint: `POST https://general.datacommons.cancer.gov/v1/graphql/` with body
`{"query": "{ queryName(args) { fields } }"}`. GC returns HTTP 200 even on query errors — inspect the
`errors` array. Arguments are GraphQL named args (strings double-quoted, ints bare, lists in `[...]`).

GC exposes **73 queries in two families** (full introspected list:
[../assets/query-fields.txt](../assets/query-fields.txt); authoritative schema:
[../assets/general-commons-schema.graphql](../assets/general-commons-schema.graphql)):

1. **Faceted search (Elasticsearch-backed)** — `searchSubjects` + the `*Overview` row queries: the
   cohort-builder, centered on the **subject**. Documented in [SEARCH.md](SEARCH.md); summarized below.
2. **Data Type Queries (Gen3-style)** — untransformed per-study records straight from the graph
   database (`participants`, `diagnoses`, `treatments`, `files`, …). The bulk of this file.

Plus repository **metrics**, per-entity **counts**, and **version/detail** helpers.

**Pagination:** every list query takes `first` (page size, default **10**, max **10000**) and `offset`
(default 0). See [PAGINATION.md](PAGINATION.md). Per-node field lists: [ENTITIES.md](ENTITIES.md) and
[DATA-TYPES.md](DATA-TYPES.md).

`phs_accession` is the dbGaP study accession (e.g. `phs001287`) and is **required** on every per-study
Data Type Query — it is marked **REQ** below.

---

## Faceted search (Bento ES) — the cohort-builder → [SEARCH.md](SEARCH.md)

Centered on the **subject** (= participant). All share a ~40-dimension facet arg set (lists; OR within a
facet, AND across facets). Full facets, return shapes, and `subjectCountBy*`/`filterSubjectCountBy*`/
`donutCountBy*` are in [SEARCH.md](SEARCH.md).

| Query | Returns | Use |
|---|---|---|
| `searchSubjects(...facets, search_text)` | `SearchResult` | Counts + per-facet group counts (`GroupCount { group subjects }`). **Not paged; no record rows.** |
| `subjectOverview(...facets + paging)` | `[SubjectOverview]` | Paged subject rows (incl. `samples`, `files` as DRS ids). |
| `sampleOverview(...facets + paging)` | `[SampleOverview]` | Paged sample rows. |
| `fileOverview(...facets + paging)` | `[FileOverview]` | Paged file rows. |
| `protocolOverview(...facets + paging)` | `[ProtocolOverview]` | Paged protocol rows. |
| `filesInList(...facets + paging)` | `[FilesInList]` | File rows **with `drs_uri`** + `associated_*` — build a download manifest ([FILES.md](FILES.md)). |
| `fileIDsFromList(subject_ids, sample_ids, file_names, file_ids, study_participant_ids, protocol_pk_ids)` | `[String]` | Resolve mixed ids → file ids. |
| `idsLists` / `findSubjectIdsInList(subject_ids)` | `IdsLists` / `[SubjectResult]` | Subject id helpers. |

> Faceted bucket counts use the field name **`subjects`**, not `count`.

## Repository metrics (no args)

`numberOfStudies`, `numberOfSubjects`, `numberOfSamples`, `numberOfFiles`, `numberOfDiseaseSites`,
`numberOfImages`, `numberOfProteomics` → `Int`. (These are repository-wide; `searchSubjects` returns the
same metric names scoped to a filter.) `idsLists` → `{ subjectIds }`.

---

# Data Type Queries

---

## Program / study (no `phs_accession` needed)

### `programs`
List of Program records. Args: `program_names` ([String], optional), `first`, `offset`.
Fields: `program_name program_acronym program_short_name program_short_description
program_full_description program_external_url institution crdc_id`.

### `studies`
List of Study records — the entry point for resolving a `phs_accession`. Args: `phs_accessions`
([String]), `study_names` ([String]), `study_acronyms` ([String]), `first`, `offset` (all optional).
Key fields: `phs_accession study_id study_name study_acronym study_description short_description
study_external_url primary_investigator_name funding_agency organism_species adult_or_childhood_study
data_access_level study_access acl authz number_of_participants number_of_samples study_data_types
file_types_and_format study_version crdc_id`. (Full list in [ENTITIES.md](ENTITIES.md).)

---

## Clinical / biospecimen (per study)

### `participants`
Participant (patient/donor) records. Args: `participant_ids` ([String]), **`phs_accession` REQ**,
`first`, `offset`.
Fields: `participant_id study_participant_id race sex ethnicity dbGaP_subject_id crdc_id phs_accession`.

### `diagnoses`
Diagnosis records. Args: `diagnosis_ids` ([String]), **`phs_accession` REQ**, `participant_ids`
([String]), `first`, `offset`.
Fields include: `diagnosis_id disease_type primary_diagnosis primary_site vital_status age_at_diagnosis
tumor_grade tumor_stage_clinical_t/_n/_m morphology tissue_or_organ_of_origin
site_of_resection_or_biopsy progression_or_recurrence days_to_recurrence days_to_last_followup
last_known_disease_status participant_id phs_accession`.

### `treatments`
Treatment records. Args: `treatment_ids` ([String]), **`phs_accession` REQ**, `participant_ids`
([String]), `first`, `offset`.
Fields: `treatment_id treatment_type therapeutic_agents days_to_treatment response participant_id
phs_accession crdc_id`.

### `samples`
Sample (biospecimen) records. Args: `sample_ids` ([String]), **`phs_accession` REQ**, `participant_ids`
([String]), `first`, `offset`.
Fields: `sample_id sample_type sample_type_category sample_tumor_status sample_anatomic_site
sample_description sample_age_at_collection derived_from_specimen tumor_classification
biosample_accession Organization_Name participant_id phs_accession crdc_id`.

---

## Files & sequencing (per study)

### `files`
File records — the main file query. Args: `file_ids` ([String]), `file_names` ([String]), `file_types`
([String]), `released_range_start` (String `YYYY-MM-DD`), `released_range_end` (String `YYYY-MM-DD`),
**`phs_accession` REQ**, `participant_ids` ([String]), `first`, `offset`.
Fields: `file_id file_name file_type file_description file_size md5sum checksum_value checksum_algorithm
file_url_in_cds experimental_strategy_and_data_subtypes file_mapping_level release_datetime
is_supplementary_file submission_version crdc_id phs_accession participant_ids`. See [FILES.md](FILES.md)
— `file_id` is a DRS id and the API does **not** download.

### `genomic_info`
Sequencing/library metadata attached to files. Args: `genomic_info_ids` ([String]),
**`phs_accession` REQ**, `file_ids` ([String]), `first`, `offset`.
Fields: `genomic_info_id library_id library_strategy library_layout library_selection
library_source_material library_source_molecule platform instrument_model design_description bases
number_of_reads avg_read_length coverage reference_genome_assembly
custom_assembly_fasta_file_for_alignment sequence_alignment_software methylation_platform
reporter_label file_id phs_accession crdc_id`.

---

## Proteomics / PDX (per study)

### `proteomics`
Proteomic run metadata attached to files. Args: `proteomic_info_ids` ([String]), **`phs_accession`
REQ**, `file_ids` ([String]), `first`, `offset`.
Fields: `proteomic_info_id aliquot_id analytical_fractions instrument_make proteomic_instrument_model
proteomic_design_description manufacturer_model_name file_id phs_accession crdc_id`. (For real
proteomics quantitation, use `proteomic-data-commons`.)

### `pdx`
Patient-derived xenograft models attached to samples. Args: `pdx_ids` ([String]), **`phs_accession`
REQ**, `sample_ids` ([String]), `first`, `offset`.
Fields: `pdx_id model_id implantation_type implantation_site mouse_strain sample_type_for_implantation
tumor_not_mus_or_ebv_origin sample_id phs_accession`.

---

## Imaging modalities (per study)

All take **`phs_accession` REQ**, `file_ids` ([String]), `first`, `offset`, plus an id arg. (For image
*pixels*, use the imaging-data-commons; these queries are GC's image *metadata*.) See
[DATA-TYPES.md](DATA-TYPES.md).

| Query | Id arg | Node |
|---|---|---|
| `images` | `study_link_ids` | Image (modality, equipment, de-identification) |
| `multiplex_microscopies` | `multiplex_microscopy_ids` | MultiplexMicroscopy (channel/antibody/fluorophore) |
| `non_dicomct_images` | `non_dicomct_images_ids` | NonDICOMCTimages |
| `non_dicommr_images` | `non_dicommr_images_ids` | NonDICOMMRimages |
| `non_dicompet_images` | `non_dicompet_images_ids` | NonDICOMPETimages |
| `non_dicom_pathology_images` | `non_dicom_pathology_images_ids` | NonDICOMpathologyImages |
| `non_dicom_radiology_all_modalities` | `non_dicom_radiology_all_modalities_ids` | NonDICOMradiologyAllModalities |

---

## Study extras (caNanoLab / NCIcaNano and study metadata)

These are in the backend schema and live. Several back the caNanoLab/NCIcaNano nanomaterials program.
All take `first`/`offset`.

| Query | Id arg + scope | Node fields (highlights) |
|---|---|---|
| `investigators` | `investigator_ids`, `phs_accession` | `investigator_id primary_investigator_name role_or_affiliation email` |
| `characterizations` | `characterization_ids`, `phs_accession`, `sample_ids` | `Characterization_ID Characterization_Assay_Type Characterization_Name` |
| `publications` | `publication_ids`, `phs_accession`, `sample_ids` | `DOI_or_Pub_ID Publication_Type Publication_Status Publication_Title` |
| `protocols` | `protocol_ids`, `phs_accession`, `file_ids`, `sample_ids` | `protocol_pk_id protocol_name protocol_type doi` |
| `compositions` | `composition_ids`, `phs_accession`, `sample_ids` | `Composition_ID Nanomaterial_Entity_Type Functionalizing_Entity_Type` |
| `consent_groups` | `consent_group_ids`, `phs_accession` | consent-group metadata |

Their per-study count cousins also exist: `investigatorsCount`, `characterizationsCount`,
`publicationsCount`, `protocolsCount`, `compositionsCount`, `consentGroupsCount` (each needs
`phs_accession`).

---

## Count queries

- **No args:** `programsCount`, `studiesCount`, `versionsCount`.
- **Require `phs_accession`:** `participantsCount`, `samplesCount`, `filesCount`, `diagnosesCount`,
  `treatmentsCount`, `imagesCount`, `genomicInfoCount`, `proteomicsCount`, `pdxCount`,
  `multiplexMicroscopiesCount`, `nonDICOMCTimagesCount`, `nonDICOMMRimagesCount`,
  `nonDICOMPETimagesCount`, `nonDICOMpathologyImagesCount`, `nonDICOMradiologyAllModalitiesCount`
  (+ the study-extra counts above).

Counts are the cheap way to size a study before pulling records.

---

## Version queries

- `version` → Version node: `data_version model_version datetime description data_version_id crdc_id`.
- `schemaVersion` → String (GraphQL API schema version, e.g. `3.1.0`).
- `schemaModelVersion` → String (data model version baked into the schema). **Note:** this can lag the
  live data's `version.model_version` — trust `version` for the current data release.

---

## Discovery & detail helpers

Portal-facing summary/detail views — handy for discovery (the faceted-search family is documented
separately in [SEARCH.md](SEARCH.md)):

- `globalSearch(input: "<text>" first offset)` → free-text hits bucketed into `studies subjects samples
  files programs about_page model` with per-bucket counts (`study_count`, `subject_count`, …). The
  fastest "is this in GC?" check.
- `programList { acronym name website num_studies }` → flat program list with study counts.
- `studyList { study_name phs_accession data_type numberOfSubjects numberOfFiles study_access
  study_version }` → flat study list.
- `programDetail(program_name: "...")` → program summary with its studies and per-study counts.
- `studyDetail(phs_accession: "...")` → one study's summary (`study_acronym study_description
  data_types study_external_url numberOfSubjects numberOfSamples numberOfFiles numberOfDiseaseSites`).
- `subjectDetail(subject_id: "...")` → one subject with its `files` and `samples` nested.
- `samplesForSubjectId(subject_id: "...")` → `[Sample]` for a subject.
