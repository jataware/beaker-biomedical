# Faceted study search (`searchStudies`)

`searchStudies` answers "which studies match X" and exposes the facet landscape. It faces over
**studies, not participants** (the participant-level facet families exist in the schema but currently
error — see [../references/QUERIES.md](../references/QUERIES.md)). Uses the `psdc()` helper from
[quickstart.md](quickstart.md). Reference: [../references/SEARCH.md](../references/SEARCH.md).

## See the landscape (no filter)

Each bucket is `{ group, subjects }` where **`subjects` = number of studies** in that group.

```python
land = psdc("""
{ searchStudies {
    numberOfStudies numberOfDiagnosis dataVolume
    studyCountByStudyDesign { group subjects }
    studyCountByNeoplasm { group subjects } } }
""")["searchStudies"]
print(land["numberOfStudies"], "studies,", land["numberOfDiagnosis"], "diagnoses")
# 3 studies, 40 diagnoses
print([(g["group"], g["subjects"]) for g in land["studyCountByStudyDesign"]])
# [('Case-Control Study', 1), ('Clinical Trial', 1), ('Cohort Study - Prospective', 1)]
print([(g["group"], g["subjects"]) for g in land["studyCountByNeoplasm"][:4]])
# [('Not Applicable', 3), ('breast', 2), ('lung', 2), ('abdomen', 1)]   # studies touching each site
```

## Filter (the argument names are snake_case study properties)

The filter **arguments** differ from the `studyCountBy*` field names — e.g. design is `study_design`
and the neoplasm-site facet is `cancer_diagnosis_primary_site_list`. All are lists.

```python
psdc('{ searchStudies(study_design: ["Clinical Trial"]) '
     '{ numberOfStudies filterStudyCountByStudy { group subjects } } }')["searchStudies"]
# {'numberOfStudies': 1, 'filterStudyCountByStudy': [{'group': 'NLST', 'subjects': 1}]}

psdc('{ searchStudies(cancer_diagnosis_primary_site_list: ["lung"]) '
     '{ numberOfStudies filterStudyCountByStudy { group subjects } } }')["searchStudies"]
# {'numberOfStudies': 2, 'filterStudyCountByStudy': [{'group': 'NLST', 'subjects': 1}, {'group': 'PLCO', 'subjects': 1}]}
```

Useful filter args (all lists): `study_short_name`, `study_design`, `study_type`, `study_status`,
`biospecimen_collection`, `data_collection_category`, `dbgap_accession_id`, `study_country`,
`cancer_diagnosis_primary_site_list`, `race`, `ethnicity`, `sex`, `number_of_participants`,
`study_participant_{minimum,median,maximum}_age`, and the enrollment/study year args.

## Numeric ranges & slider bounds

`searchStudies` also returns `studyPeriodMin`/`Max`, `enrollmentPeriodMin`/`Max`,
`participantAgeAtEnrollmentMin`/`Max`, and `studyCountByNumberOfParticipants`. The absolute bounds
across all studies come from `minMaxBoundQuery`:

```python
psdc("{ minMaxBoundQuery { number_of_participant_lower_bound number_of_participant_upper_bound "
     "participant_maximum_age_upper_bound } }")
# [{'number_of_participant_lower_bound': 4886, 'number_of_participant_upper_bound': 151383,
#   'participant_maximum_age_upper_bound': 79}]
```

## Notes

- With only 3 studies loaded, facet counts are small; the value is discovering exact vocabulary values
  and confirming which studies touch a site/design.
- `subjects` here means **studies**, not people — don't report it as a participant count.
- For per-study detail once you've picked a study, switch to the study-level queries
  ([explore_studies.md](explore_studies.md)).
