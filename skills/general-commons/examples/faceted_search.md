# Build a cohort with faceted search

GC's Bento **faceted-search** layer (`searchSubjects` + the `*Overview` queries) is the way to find a
cohort by characteristic **across studies** — the equivalent of the portal's Explore page. Use the
`gc()` helper from [quickstart.md](quickstart.md). Facet reference: [../references/SEARCH.md](../references/SEARCH.md).

> "subject" here = the "participant" of the Data Type Queries. Use this layer to *find* the cohort,
> then the Data Type Queries ([study_clinical.md](study_clinical.md)) to pull its structured records.

## Step 1 — see the landscape (discover valid facet values)

`searchSubjects` with no filter returns repository-wide facet counts. **Each bucket's count field is
`subjects`, not `count`.** Use this to learn the controlled-vocabulary values before filtering.

```python
land = gc("""
{ searchSubjects {
    numberOfStudies numberOfSubjects numberOfFiles
    subjectCountByPrimaryDiagnosis { group subjects }
    subjectCountBySex { group subjects }
    subjectCountByExperimentalStrategy { group subjects } } }
""")["searchSubjects"]
print(land["numberOfSubjects"], "subjects total")          # 120867
for g in land["subjectCountByPrimaryDiagnosis"][:5]:
    print(g["subjects"], g["group"])
```

## Step 2 — narrow with facet args (lists; OR within a facet, AND across facets)

`searchSubjects` returns the post-filter counts (`filterSubjectCountBy*`) so you can see which studies
and sexes remain, plus the summary metrics for the cohort.

```python
cohort = gc("""
{ searchSubjects(primary_diagnoses: ["Glioblastoma, NOS"]) {
    numberOfStudies numberOfSubjects numberOfFiles
    filterSubjectCountByPhsAccession { group subjects }
    filterSubjectCountBySex { group subjects } } }
""")["searchSubjects"]

print(cohort["numberOfStudies"], "studies,", cohort["numberOfSubjects"], "subjects,",
      cohort["numberOfFiles"], "files")
# 5 studies, 867 subjects, 746 files
print([(g["group"], g["subjects"]) for g in cohort["filterSubjectCountByPhsAccession"][:4]])
# [('phs002790', 519), ('phs002431', 208), ('phs003215', 10), ('phs002518', 8)]
```

This already answers "which GC studies have glioblastoma, and how many subjects each" — without a
disease filter on the `studies` query.

## Step 3 — pull the rows (paged; default `first: 10`, so set it)

`subjectOverview` takes the **same facet args** plus paging. Loop `offset` for the full set.

```python
def all_subjects(**facets):
    rows, off, size = [], 0, 200
    args = " ".join(f'{k}: {v!r}'.replace("'", '"') for k, v in facets.items())
    while True:
        q = ("{ subjectOverview(%s first: %d offset: %d order_by: \"subject_id\") "
             "{ subject_id phs_accession sex primary_diagnosis samples files } }")
        page = gc(q % (args, size, off))["subjectOverview"]
        rows += page
        if len(page) < size:
            return rows
        off += size

subs = all_subjects(primary_diagnoses=["Glioblastoma, NOS"])
print(len(subs), "subjects")
print(subs[0])
# {'subject_id': '00301d78915737fa100f', 'phs_accession': ['phs002431'], 'sex': 'Female',
#  'primary_diagnosis': ['Glioblastoma, NOS'], 'samples': [...], 'files': ['dg.4DFC/...', ...]}
```

`sampleOverview` and `fileOverview` work identically for sample- and file-level rows. The
`subjectOverview.files` are CRDC **DRS ids** (`dg.4DFC/<uuid>`).

## Step 4 — assemble a download manifest

`filesInList` returns the same file rows **with `drs_uri`** ready for the Cancer Genomics Cloud:

```python
files = gc("""
{ filesInList(primary_diagnoses: ["Glioblastoma, NOS"], file_types: ["BAM"], first: 1000) {
    file_name file_type file_size file_id drs_uri accesses phs_accession } }
""")["filesInList"]
# each row: file_id "dg.4DFC/…", drs_uri "drs://nci-crdc.datacommons.io/dg.4DFC/…", accesses ["Controlled"|"Open"]
```

Controlled-access files still need dbGaP authorization to *retrieve* (metadata is always open). See
[../references/FILES.md](../references/FILES.md).

## Notes

- Facet args are **lists** even for one value: `sex: ["Female"]`, not `sex: "Female"`.
- The ~40 facet dimensions + `subjectCountBy*` vs `filterSubjectCountBy*` vs `donutCountBy*` are in
  [../references/SEARCH.md](../references/SEARCH.md).
- For structured per-study records (diagnoses, treatments, sequencing metadata), switch to the Data
  Type Queries with the `phs_accession` values you found here — see [study_clinical.md](study_clinical.md).
