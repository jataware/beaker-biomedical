# Build a cohort with faceted search

The common task: "find me the participants/specimens/files matching these criteria." Use
`searchParticipants` to see the facet landscape, narrow, then pull rows. Uses the `ctdc()` helper from
[quickstart.md](quickstart.md). Facet reference: [../references/SEARCH.md](../references/SEARCH.md).

## Step 1 — see the landscape (discover valid facet values)

`searchParticipants` with no filter returns repository-wide facet counts. **Each bucket's count field
is `subjects`, not `count`.**

```python
land = ctdc("""
{ searchParticipants {
    numberOfParticipants numberOfSpecimens numberOfFiles
    participantCountByCtepDiseaseTerm { group subjects }
    participantCountByTargetedTherapy { group subjects }
    specimenCountBySpecimenType { group subjects } } }
""")["searchParticipants"]
for g in land["participantCountByCtepDiseaseTerm"][:4]:
    print(g["subjects"], g["group"])
# 64 Plasma Cell Myeloma / 52 Non-Small Cell Lung Carcinoma / 50 Colorectal Carcinoma / 45 Melanoma
```

## Step 2 — narrow with facet args (lists; OR within a facet, AND across facets)

`searchParticipants` returns the post-filter counts (`filterParticipantCountBy*`) so you can see what's
left to refine, plus the cohort's summary metrics.

```python
cohort = ctdc("""
{ searchParticipants(ctep_disease_term: ["Melanoma"]) {
    numberOfParticipants numberOfSpecimens numberOfFiles
    filterParticipantCountBySex { group subjects }
    filterParticipantCountByTargetedTherapy { group subjects } } }
""")["searchParticipants"]

print(cohort["numberOfParticipants"], "participants,", cohort["numberOfSpecimens"], "specimens,",
      cohort["numberOfFiles"], "files")
# 45 participants, 189 specimens, 450 files
print([(g["group"], g["subjects"]) for g in cohort["filterParticipantCountByTargetedTherapy"][:4]])
# [('Nivolumab', 16), ('Pembrolizumab', 16), ('Not Reported', 11), ('Dabrafenib', 5)]
```

## Step 3 — pull the rows (paged; default `first: 10`, so set it)

`participantOverview` takes the **same facet args** plus paging. Loop `offset` for the full set.

```python
def all_participants(**facets):
    rows, off, size = [], 0, 100
    args = " ".join(f'{k}: {v!r}'.replace("'", '"') for k, v in facets.items())
    while True:
        q = ("{ participantOverview(%s first: %d offset: %d order_by: \"participant_id\") "
             "{ participant_id ctep_disease_term stage_of_disease sex race age_at_enrollment "
             "targeted_therapy } }")
        page = ctdc(q % (args, size, off))["participantOverview"]
        rows += page
        if len(page) < size:
            return rows
        off += size

mel = all_participants(ctep_disease_term=["Melanoma"])
print(len(mel), "participants")
print(mel[0])
# {'participant_id': 'MSB-00205', 'ctep_disease_term': 'Melanoma', 'stage_of_disease': None,
#  'sex': 'Male', 'race': 'White', 'age_at_enrollment': 63.0, 'targeted_therapy': '[Not Reported]'}
```

**Note `targeted_therapy` is a bracketed string**, not a list — parse it yourself
(`row["targeted_therapy"].strip("[]").split(", ")`). Same for `anatomical_collection_site`,
`tissue_category`, etc. (see [../references/ENTITIES.md](../references/ENTITIES.md)).

Use `biospecimenOverview` / `fileOverview` the same way for specimen- and file-level rows.

## Step 4 — hand off to specimens / files

Pull the cohort's biospecimens or files with the same facet filter, then assemble a download list:

```python
files = ctdc('{ fileOverview(ctep_disease_term: ["Melanoma"], first: 1000) '
             '{ data_file_uuid drs_uri data_file_name data_file_format data_file_size } }')["fileOverview"]
```

See [files_and_download.md](files_and_download.md).

## Notes

- Facet args are **lists** even for one value: `sex: ["Male"]`, not `sex: "Male"`.
- `participantCountBy*` = whole-repository landscape; `filterParticipantCountBy*` = after your filter.
- Specimen/file buckets count specimens/files (not participants) — they sum above the participant total.
- The ~16 facet dimensions are in [../references/SEARCH.md](../references/SEARCH.md).
