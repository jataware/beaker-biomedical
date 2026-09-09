# Discover studies

CTDC is small and study-rooted — start by listing the studies, then drill in or pivot to a cohort.
Uses the `ctdc()` helper from [quickstart.md](quickstart.md).

## List every study with counts

```python
ctdc("""
{ getAllStudies {
    study_short_name study_name study_type dates_of_conduct
    participant_count study_file_count participant_file_count image_collection_count } }
""")["getAllStudies"]
# [{'study_short_name': 'CMB', 'study_name': 'CM Biobank', 'study_type': 'Observational Study',
#   'participant_count': 248, 'study_file_count': 1, 'participant_file_count': 2033, ...}]
```

As of this writing there is one study (`CMB`); expect the set to grow — always call it live.

## One study's full record

```python
ctdc('''
{ studyByStudyShortName(study_short_name: "CMB") {
    study_short_name study_name study_type dates_of_conduct
    participant_count study_file_count participant_file_count
    principal_investigators { person_first_name person_last_name person_orcid }
    publications { publication_title pubmed_id }
    consent_groups { consent_group_name }
    associated_links { associated_link_name associated_link_url } } }
''')["studyByStudyShortName"][0]
# {'study_name': 'CM Biobank', 'study_type': 'Observational Study',
#  'dates_of_conduct': 'September 2020 - September 2025 (estimated)',
#  'participant_count': 248, 'study_file_count': 1, 'participant_file_count': 2033, ...}
```

`studyByStudyShortName` returns a **list** — take `[0]`.

## A study's diagnoses / specimens / files at a glance

```python
ctdc('{ studyDiagnosisByStudyShortName(study_short_name: "CMB") { ctep_disease_terms } }')
ctdc('{ StudySpecimenByStudyShortName(study_short_name: "CMB") '
     '{ specimen_count specimen_types { group count } specimen_timepoints { group count } } }')
ctdc('{ StudyDataFileByStudyShortName(study_short_name: "CMB") { list_type } }')
```

Note the **capital `S`** on `StudySpecimenByStudyShortName` / `StudyDataFileByStudyShortName`, and that
these per-study summary counts use `count` (not the `subjects` of the faceted layer).

## Free-text search

`globalSearch` spans participants, biospecimens, help pages, and the data model — good when the user's
term could be a disease or therapy:

```python
gs = ctdc('{ globalSearch(input: "melanoma", first: 3) '
          '{ participant_count biospecimen_count participants { participant_id } } }')["globalSearch"]
print(gs["participant_count"], "participants,", gs["biospecimen_count"], "biospecimens")
# 45 participants, 189 biospecimens
```

## Next

- Build a cohort by disease/therapy/specimen trait → [faceted_search.md](faceted_search.md).
- Pull a study's structured longitudinal records → [clinical_data.md](clinical_data.md).
