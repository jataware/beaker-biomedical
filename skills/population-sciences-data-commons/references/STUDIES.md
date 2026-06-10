# Studies & the study-level data model

PS-DC is, today, a **study-level** API: the working queries describe the three studies (their design,
size, demographics, cancer sites, data-collection scope, and study-level files), not individual
participants. `study_short_name` (`NLST`, `PLCO`, `PBCS`) is the key argument throughout.

## The three studies (live via `globalStatsBar`)

| `study_short_name` | Name | Design | Participants | `cancer_type_count` |
|---|---|---|---|---|
| `NLST` | National Lung Screening Trial | Clinical Trial | 48,860 | 2 |
| `PLCO` | Prostate, Lung, Colorectal and Ovarian Cancer Screening Trial | Cohort Study – Prospective | 151,383 | 40 |
| `PBCS` | Polish Breast Cancer Study | Case-Control Study | 4,886 | 2 |

`minMaxBoundQuery` gives the cross-study slider bounds (participant count 4,886–151,383; max age 79).

## Study-level queries and their fields

All are study-keyed (`study_short_name: [String]`) and Elasticsearch-backed (they work today).

### `globalStatsBar` → `[GlobalStatsBar]` — the study cards
`study_short_name`, `number_of_participants`, `study_type`, `study_design`, `data_volume`,
`cancer_type_count`, `cancer_diagnosis_primary_site_count`, `study_cancer_diagnosis_primary_site_count_collection`.

### `tabStudy` → `[TabStudy]` — the rich study table
`study_name`, `study_short_name`, `study_id`, `study_description`, `study_type`, `study_design`,
`enrollment_beginning_year`/`enrollment_ending_year`, `study_beginning_year`/`study_ending_year`,
`biospecimen_collection` (`Yes`/`No`), `data_collection_category` ([String]), `study_status`
(`Closed`/…), `dbgap_accession_id` ([String]), `number_of_participants`,
`study_participant_minimum_age`/`_median_age`/`_maximum_age`, `race`/`ethnicity`/`sex`,
`study_country`, `number_of_countries`, `data_volume`, `data_file_total_size`,
`primary_diagnosis_disease_term`, `primary_diagnosis_disease_count`,
`cancer_diagnosis_primary_site_list`, `personnel`, `publication`, `data_file`, `associated_links`.

### `studyDemographics` → `[StudyDemographics]` — age/sex/race/ethnicity
`number_of_participants`, `participant_minimum_age`/`_median_age`/`_mean_age`/`_maximum_age`,
`participant_age_range`, `participant_count_by_age`, and `participant_sexes` / `participant_races` /
`participant_ethnicities` — each a **`[GroupCounts]`** (select `{ group subjects }`). Live NLST:

```graphql
{ studyDemographics(study_short_name: ["NLST"]) {
    number_of_participants participant_median_age
    participant_sexes { group subjects } participant_races { group subjects } } }
# 48860 participants, median age 60
# sexes: male 28414, female 20446
# races: white 44363, black or african american 2183, asian 994, unknown 963, ...
```

### `primarySiteMorphology` → `[PrimarySiteMorphology]`
`cancer_diagnosis_primary_site_collection` (`[TypeCount]`) and
`cancer_diagnosis_disease_morphology_collection` (`[DiagnosisCodes]`) per study + `data_collection_category_count`.

### `dataCollectionPage` → `[data_collection_page]`
`study_short_name` + `data_collection` — the data-collection domains a study covers (e.g. NLST lists
dozens: `Cigarette Smoking`, `Family History of Cancer`, `Dietary Intake`, `Radiation Exposure`,
`Screening`, `Measured Anthropometry`, …).

### `studyGeneral` → `[StudyGeneral]`
`personnel`, `publication`, `data_file`, `associated_links`, `primary_diagnosis_disease_count`.

### `studyFiles` → `[StudyFiles]` — study-level files (with DRS)
`study_short_name`, `data_file_name`, `data_file_type` (e.g. `Data Dictionary`), `data_file_format`
(`pdf`, …), `data_file_size`, `data_file_uuid`, **`drs_uri`**, `data_file_access_control`
(e.g. `Open Access`), `data_file_signed_url`, `data_file_checksum_value`. These are study-level
artifacts (data dictionaries, registries, manifests) — **not** participant data files. Example (PLCO):
`Breast.Registry.Dictionary.pdf` → `data_file_uuid: dg.4DFC/ec2cc19c-…`,
`drs_uri: drs://nci-crdc.datacommons.io/dg.4DFC/ec2cc19c-…`, `Open Access`.

## Getting the actual participant data

PS-DC exposes study **metadata**; the participant-level datasets for NLST/PLCO/PBCS are distributed
through **NCBI dbGaP** under each study's `dbgap_accession_id` (read it off `tabStudy`), and via the
study programs' own portals (e.g. the NCI Cancer Data Access System, CDAS, for PLCO/NLST). Study-level
files from `studyFiles` download via their CRDC DRS id
(`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`). The in-API participant/sample/file *record* queries
are not functional yet (see [QUERIES.md](QUERIES.md)).
