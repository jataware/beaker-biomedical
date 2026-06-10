# Explore the studies

The working PS-DC surface is study-level. This is the end-to-end recipe for describing NLST / PLCO /
PBCS. Uses the `psdc()` helper from [quickstart.md](quickstart.md). Field reference:
[../references/STUDIES.md](../references/STUDIES.md).

## Overview — the study cards

```python
psdc("{ globalStatsBar { study_short_name number_of_participants study_design cancer_type_count } }")
# NLST 48860 (Clinical Trial, 2) / PLCO 151383 (Cohort Study - Prospective, 40) / PBCS 4886 (Case-Control, 2)
```

## Rich study metadata (`tabStudy`)

```python
psdc('''
{ tabStudy {
    study_short_name study_name study_design study_status
    enrollment_beginning_year enrollment_ending_year
    number_of_participants biospecimen_collection dbgap_accession_id
    study_country number_of_countries
    primary_diagnosis_disease_term cancer_diagnosis_primary_site_list } }
''')["tabStudy"]
# e.g. NLST: "The National Lung Screening Trial", Clinical Trial, Closed, enrolled 2002-2004,
#      48860 participants, biospecimen_collection "Yes", dbgap_accession_id [...]
```

`dbgap_accession_id` is the handoff to the full participant dataset on NCBI dbGaP.

## Demographics (age / sex / race / ethnicity)

`participant_sexes` / `participant_races` / `participant_ethnicities` are `[GroupCounts]` — select
`{ group subjects }` (the count field is `subjects`):

```python
psdc('''
{ studyDemographics(study_short_name: ["NLST"]) {
    number_of_participants participant_median_age participant_age_range
    participant_sexes { group subjects }
    participant_races { group subjects } } }
''')["studyDemographics"][0]
# {'number_of_participants': 48860, 'participant_median_age': 60,
#  'participant_sexes': [{'group': 'male', 'subjects': 28414}, {'group': 'female', 'subjects': 20446}],
#  'participant_races': [{'group': 'white', 'subjects': 44363},
#                        {'group': 'black or african american', 'subjects': 2183},
#                        {'group': 'asian', 'subjects': 994}, {'group': 'unknown', 'subjects': 963}, ...]}
```

## Cancer sites & data-collection scope

```python
# primary cancer sites + morphology codes per study
psdc('{ primarySiteMorphology(study_short_name: ["PLCO"]) '
     '{ study_short_name cancer_diagnosis_primary_site_collection { group subjects } } }')

# which data-collection domains a study covers (questionnaires/exposures)
psdc('{ dataCollectionPage(study_short_name: ["NLST"]) { study_short_name data_collection } }')
# NLST data_collection includes: Cigarette Smoking, Family History of Cancer, Dietary Intake,
# Radiation Exposure, Screening, Measured Anthropometry, Alcohol Consumption, ... (dozens)
```

## Study-level files (with DRS ids)

`studyFiles` returns study artifacts (data dictionaries, registries, manifests) — not participant data:

```python
psdc('''
{ studyFiles(study_short_name: ["PLCO"], first: 5) {
    data_file_name data_file_type data_file_format
    data_file_uuid drs_uri data_file_access_control } }
''')["studyFiles"]
# e.g. {'data_file_name': 'Breast.Registry.Dictionary.pdf', 'data_file_type': 'Data Dictionary',
#       'data_file_format': 'pdf', 'data_file_uuid': 'dg.4DFC/ec2cc19c-...',
#       'drs_uri': 'drs://nci-crdc.datacommons.io/dg.4DFC/ec2cc19c-...',
#       'data_file_access_control': 'Open Access'}
```

Download bytes by resolving the DRS id (`drs_uri`) through CRDC DRS, e.g.
`POST https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/<GUID>/access/s3` → signed URL.

## What you can't do (yet)

Per-participant records (`subjectInfo`), per-participant cohorts (`subjectListBy*`), and file-record
queries (`fileOverview`) currently error (Neo4j backend down). For participant-level NLST/PLCO/PBCS
data, point the user to dbGaP (via `dbgap_accession_id`) or the study portals (e.g. NCI CDAS for
PLCO/NLST). See [../references/QUERIES.md](../references/QUERIES.md).
