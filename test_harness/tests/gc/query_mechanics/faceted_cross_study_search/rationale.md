# Intended Behavior

The agent uses `searchSubjects`/`subjectOverview` with the discovered value `Medulloblastoma, NOS`, reads the bucket count field as `subjects`, and reports ~8 studies across the CCDI and PDXNet programs. It reports the cohort as ~1,226 distinct subjects (`numberOfSubjects`) and either avoids or explicitly flags the inflated ~12,934 bucket total, since the `subjects` field on buckets counts records and can far exceed the true subject count.

# Incorrect Behavior

The agent asks for `count` on a facet bucket (`FieldUndefined`), hardcodes a near-miss diagnosis like `Medulloblastoma NOS` (which returns 0 with no error), reports the 12,934 bucket total as a clean patient count, or calls `subjectOverview` with no `first` and reports only its 10 rows.
