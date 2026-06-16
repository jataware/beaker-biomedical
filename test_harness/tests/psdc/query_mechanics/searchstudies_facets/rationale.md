# Intended Behavior

The agent uses `searchStudies` and its `studyCountBy*` facets, framing the bucket `subjects` field as a count of *studies*, not people. There are 3 studies and 40 diagnoses; all three report `biospecimen_collection = "Yes"` (`subjects` = 3 studies), and breast and lung are each covered by 2 studies, with ~37 single-study sites.

# Incorrect Behavior

The agent describes the facet `subjects` as numbers of people or patients (e.g. "3 biospecimen subjects", "2 breast cancer patients"), or reports the wrong study sets.
