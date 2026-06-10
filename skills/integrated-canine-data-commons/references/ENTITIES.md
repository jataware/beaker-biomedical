# ICDC data model & entities

ICDC is a Neo4j property graph surfaced through GraphQL (the Bento framework). Nodes are the
data-model entities; edges are typed relationships; the auto-generated node queries let you start at
any node, filter on its properties, and traverse edges by nesting fields. The full model is preserved
verbatim in [../assets/icdc-model.yml](../assets/icdc-model.yml) (data model v2.1.0).

## ID keys — resolve the right one first

| Entity | Key argument | Example | Notes |
|---|---|---|---|
| program | `program_acronym` | `COP`, `CMCP`, `PRECINCT`, `CSU FACC`, `PCCR` | 5 programs. |
| study | `clinical_study_designation` | `OSA01`, `COTC022`, `GLIOMA01` | The canonical study code. The `study_code` arg on convenience queries **also accepts `accession_id`** (e.g. `000006`). |
| case | `case_id` | `COTC021-0101` | Study-prefixed; unique per case. `patient_id` is the submitter's original (non-unique across studies). |
| sample | `sample_id` | — | |
| file | `uuid` / `file_uuid` | `bf7ae08f-…` | Also the DRS id `dg.4DFC/<uuid>`. |
| canine individual | `canine_individual_id` | loader-generated | Links the same dog's cases across studies. |

A wrong/misspelled key usually yields an **empty list, not an error** — confirm the key exists
(`studiesByProgram`, `program`, `searchCases`, `globalSearch`) before a per-entity pull.

## The 5 programs (live)

| Acronym | Name |
|---|---|
| `COP` | Comparative Oncology Program |
| `CMCP` | Comparative Molecular Characterization Program |
| `PRECINCT` | Pre-medical Cancer Immunotherapy Network for Canine Trials |
| `CSU FACC` | Colorado State University Flint Animal Cancer Center |
| `PCCR` | Purdue Center for Cancer Research |

Studies include `COTC007B`, `COTC021`, `COTC022`, `NCATS-COP01`, `GLIOMA01`, `MGT01`, `ORGANOIDS01`,
`OSA01`, `OSA02`, `OSA03`, `PRECINCT01`, `UBC01`, … (call `studiesByProgram` for the current 18).

## Graph structure

```
program ──member_of──< study
study   ──member_of──< study_arm ──member_of──< cohort ──member_of──< case
case    ──member_of──> study            (direct edge; some cases skip arm/cohort)
case    ──represents─> canine_individual   (one physical dog ↔ many study-specific cases)

case <─of_case──  demographic | diagnosis | enrollment | cycle | sample | file | visit |
                  adverse_event | registration
study <─of_study─ human_relevance | study_site | principal_investigator | publication | file
case  <─had_adverse_event─ adverse_event        diagnosis <─from_diagnosis─ file
sample <─of_sample─ file                         enrollment <─at_enrollment─ prior_therapy | prior_surgery | physical_exam
visit  ──of_cycle──> cycle                       visit <─on_visit─ sample | physical_exam | vital_signs | disease_extent
```

`case_id` joins per-case records; `clinical_study_designation` joins per-study records. A `file` can
attach at study, case, sample, or diagnosis level (`numberOfStudyFiles` are study-level; the rest are
case-level).

## Nodes and their key fields

Use `{ __type(name:"<node>"){ fields { name } } }` for the exhaustive list. Highlights:

### Administrative / study
- **program** — `program_acronym`, `program_name`, `program_short_description`,
  `program_full_description`, `program_external_url`.
- **study** — `clinical_study_designation`, `clinical_study_name`, `clinical_study_description`,
  `clinical_study_type` (`Clinical Trial` / `Genomics` / `Transcriptomics` / combos),
  `accession_id`, `study_disposition` (`Unrestricted`), `date_of_iacuc_approval`, `dates_of_conduct`.
- **study_arm** — `arm`, `arm_description`, `ctep_treatment_assignment_code`, `arm_id`.
- **cohort** — `cohort_description`, `cohort_dose`, `cohort_id`.
- **principal_investigator** — `pi_first_name`, `pi_last_name`, `pi_middle_initial`.
- **publication** — `publication_title`, `authorship`, `year_of_publication`, `journal_citation`,
  `digital_object_id`, `pubmed_id`.
- **study_site** — `site_short_name`, `veterinary_medical_center`, `registering_institution`.
- **human_relevance** — `human_relevance_statement`, `relevant_human_cancer`,
  `relevant_experimental_therapeutic_intervention`, `relevant_human_genes`, `relevant_human_pathways`,
  `nci_link_to_relevant_human_cancer`. **The comparative-oncology bridge to human cancer.**

### Case / patient
- **case** — `case_id`, `patient_id`, `patient_first_name`.
- **demographic** — `breed`, `additional_breed_detail`, `sex`, `neutered_indicator`,
  `patient_age_at_enrollment` (+ `_unit`/`_original`), `weight` (kg, + units), `date_of_birth`.
- **diagnosis** — `disease_term`, `primary_disease_site`, `stage_of_disease`, `date_of_diagnosis`,
  `histology_cytopathology`, `histological_grade`, `best_response`, `concurrent_disease`(_type),
  `pathology_report`, `treatment_data`, `follow_up_data` (these last three are Yes/No availability flags).
- **enrollment** — `date_of_registration`, `date_of_informed_consent`, `site_short_name`,
  `veterinary_medical_center`, `registering_institution`, `patient_subgroup`, `initials`.
- **registration** — `registration_origin`, `registration_id` (alternate IDs for multi-study linkage).
- **canine_individual** — `canine_individual_id` only.

### Biospecimen
- **sample** — `sample_id`, `sample_site`, `physical_sample_type`, `general_sample_pathology`,
  `specific_sample_pathology`, `tumor_sample_origin`, `summarized_sample_type`, `molecular_subtype`,
  `tumor_grade`, `sample_chronology`, `necropsy_sample`, `date_of_sample_collection`,
  `length/width/volume_of_tumor`, `percentage_tumor`, `sample_preservation`, `comment`.
- **biospecimen_source** — `biospecimen_repository_acronym` → `biospecimen_repository_full_name`
  (lookup table for biobank names).

### Data files
- **file** — `file_name`, `file_type` (e.g. `RNA Sequence File`, `Index File`), `file_format`
  (`bam`, `bai`, `vcf`, `fastq`, …), `file_size` (bytes, Float), `md5sum`, `file_status`, `uuid`,
  `file_location` (`s3://…`). DRS id / `acl` are exposed via `fileDetail`/`fileInfo`, not the raw
  node. See [FILES.md](FILES.md).

### Clinical-trial event nodes → [CLINICAL.md](CLINICAL.md)
`visit` (`visit_date`,`visit_number`,`visit_id`), `cycle` (`cycle_number`,`date_of_cycle_start/end`),
`adverse_event`, `physical_exam`, `vital_signs`, `disease_extent`, `prior_therapy`, `prior_surgery`.

## Node-query usage

Exact-match property arg + traversal by nesting. Relationship field names mirror the model and are
**plural where the edge is many-valued, singular where it's to-one**. On `case`: `study`, `study_arm`,
`cohort`, `demographic`, `enrollment`, `canine_individual` (single) vs `diagnoses`, `samples`, `files`,
`visits`, `cycles`, `registrations`, `adverse_events` (lists). On `canine_individual`: `cases` (plural).
Introspect a node's fields to confirm: `{ __type(name:"case"){ fields { name } } }`.

```graphql
{ study(clinical_study_designation: "OSA01") {
    clinical_study_name accession_id clinical_study_type } }

{ case(case_id: "COTC022-2213") {           # returns a LIST; node queries always do
    study { clinical_study_designation } demographic { breed sex }
    diagnoses { disease_term } samples { sample_id } } }
```

For ranges, lists, substrings, and boolean logic use the `filter` object (`field_in`, `field_contains`,
`AND`/`OR`/`NOT`, …) — see [PAGINATION.md](PAGINATION.md). Set `first` on large nodes (a bare
`{ case { case_id } }` returns all 1,029).
