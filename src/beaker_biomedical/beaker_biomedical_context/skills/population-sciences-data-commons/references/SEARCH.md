# Faceted study search (`searchStudies`)

`searchStudies` is PS-DC's working faceted search — but note it faces over **studies, not
participants** (the participant-level `searchSubjects`-style families exist in the schema but currently
error). With only 3 studies loaded it's modest, but it's the right tool for "which studies match X" and
for discovering the controlled-vocabulary values.

```graphql
{ searchStudies { numberOfStudies numberOfDiagnosis dataVolume
    studyCountByStudyDesign { group subjects }
    studyCountByNeoplasm { group subjects } } }
```

## `searchStudies` → `SearchResult`

Takes the study facet arguments (lists; OR within a facet, AND across). Returns:

1. **Counts for the filter:** `numberOfStudies`, `numberOfDiagnosis`, `numberOfDataCollectionCatagory`
   (sic), `numberOfDataFiles`, `dataVolume`.
2. **Numeric ranges:** `studyPeriodMin`/`Max`, `enrollmentPeriodMin`/`Max`,
   `participantAgeAtEnrollmentMin`/`Max`, and `studyCountByNumberOfParticipants`.
3. **Per-facet group counts**, two parallel families — each bucket is `GroupCount { group subjects }`
   where **`subjects` = number of studies** in that group (not people):
   - `studyCountBy<Facet>` — over all studies; `filterStudyCountBy<Facet>` — after the current filter.
   - Facets: `Study`, `StudyType`, `StudyDesign`, `Neoplasm`, `Countries`, `DataCollection`,
     `BiospecimenCollection`, `Race`, `Ethnicity`, `Sex`, plus `neoplasmCountByStudy` /
     `filterNeoplasmCountByStudy`.

**The filter ARGUMENT names differ from the `studyCountBy*` field names** — the args are snake_case
study properties. The useful ones: `study_short_name`, `study_design`, `study_type`, `study_status`,
`biospecimen_collection`, `data_collection_category`, `dbgap_accession_id`, `study_country`,
`cancer_diagnosis_primary_site_list` (the "neoplasm" facet), `race`, `ethnicity`, `sex`,
`number_of_participants`, `study_participant_{minimum,median,maximum}_age`, and the year args. All are
lists. Verified live:

```graphql
{ searchStudies(study_design: ["Clinical Trial"]) { numberOfStudies } }          # → 1 (NLST)
{ searchStudies(cancer_diagnosis_primary_site_list: ["lung"]) { numberOfStudies } }  # → 2 (NLST, PLCO)
```

Live (no filter):

```
numberOfStudies 3, numberOfDiagnosis 40, dataVolume 10095885
studyCountByStudyDesign: Case-Control Study 1, Clinical Trial 1, Cohort Study - Prospective 1
studyCountByNeoplasm:    Not Applicable 3, breast 2, lung 2, abdomen 1, brain 1, colorectum 1, ...
```

So `studyCountByNeoplasm` counts **how many of the 3 studies touch each primary site** (lung appears in
NLST + PLCO; breast in PBCS + PLCO; etc.) — not patient counts.

## Discovering valid facet values

Read them off the unfiltered `studyCountBy*` buckets before filtering, then pass exact strings via the
matching snake_case argument:

```graphql
{ searchStudies(study_design: ["Clinical Trial"]) {
    numberOfStudies filterStudyCountByNeoplasm { group subjects } } }
```

Introspect the `searchStudies` field args (with the `variables` key) if unsure of an argument name:
`{ __schema { queryType { fields { name args { name } } } } }`.

## When to use what

- "What studies are in PS-DC / how many touch lung cancer?" → `searchStudies` facets (or `globalStatsBar`).
- "Details of one study (design, demographics, sites, files)?" → the study-level queries in [STUDIES.md](STUDIES.md).
- "Participant-level cohort by ER status / recurrence score / …?" → **not available yet** — those
  `subjectListBy*` / `subjectCountBy*` queries are defined but currently error ([QUERIES.md](QUERIES.md)).
