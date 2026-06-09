# GC query catalogue

Single endpoint: `POST https://general.datacommons.cancer.gov/v1/graphql/` with body
`{"query": "{ queryName(args) { fields } }"}`. GC returns HTTP 200 even on query errors — inspect the
`errors` array. Arguments are GraphQL named args (strings double-quoted, ints bare, lists in `[...]`).

The queries below are the documented **Data Type Queries** (untransformed records straight from the GC
Memgraph database) plus the count and version queries. A few live queries beyond the official doc are
noted as such. There are also **UI/transform queries** (`globalSearch`, `*Overview`, `studyList`, …)
covered under "Discovery helpers"; prefer the Data Type Queries for structured pulls.

**Pagination:** every list query takes `first` (page size, default **10**, max **10000**) and `offset`
(default 0). See [PAGINATION.md](PAGINATION.md). Per-node field lists: [ENTITIES.md](ENTITIES.md) and
[DATA-TYPES.md](DATA-TYPES.md).

`phs_accession` is the dbGaP study accession (e.g. `phs001287`) and is **required** on every per-study
query — it is marked **REQ** below.

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

## Study extras — live but **not** in the official doc

These exist in the live schema (verified) though they're absent from the upstream Data Type Queries
doc. Several back the caNanoLab/NCIcaNano nanomaterials program. All take `first`/`offset`.

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

## Discovery helpers (UI/transform queries — use sparingly)

Not Data Type Queries (they transform data for the portal), but handy for discovery:

- `globalSearch(input: "<text>" first offset)` → free-text hits bucketed into `studies subjects samples
  files programs about_page model` with per-bucket counts. The fastest "is this in GC?" check.
- `programList { acronym name website num_studies }` → flat program list with study counts.
- `studyList { study_name phs_accession data_type numberOfSubjects numberOfFiles study_access
  study_version }` → flat study list.
- `studyDetail(phs_accession: "...")`, `subjectDetail(subject_id: "...")` → portal detail views.
- `searchSubjects(...)`, `subjectOverview/sampleOverview/fileOverview(...)` → faceted cohort search with
  a large shared filter arg set (`experimental_strategies`, `file_types`, `sex`, `sample_types`,
  `primary_diagnoses`, `study_data_types`, `accesses`, `acl`, …) plus `order_by`/`sort_direction`.
  These mirror the portal's filter UI; reach for them only when a faceted cross-study search is needed.
</content>
