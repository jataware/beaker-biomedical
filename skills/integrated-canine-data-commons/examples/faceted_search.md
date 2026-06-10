# Build a cohort with faceted search

The common task: "find me all the cases of X with trait Y." Don't assume one study — use the
Elasticsearch-backed `searchCases` to see the facet landscape, narrow, then pull rows. Uses the
`icdc()` helper from [quickstart.md](quickstart.md). Facet reference: [../references/SEARCH.md](../references/SEARCH.md).

## Step 1 — see the landscape (which breeds/diagnoses/studies exist, and how many cases)

`searchCases` with no filter returns repository-wide facet counts. Inspect before you filter so you use
real controlled-vocabulary values (a wrong value returns an empty result with no error).

```python
land = icdc("""
{ searchCases {
    numberOfCases numberOfSamples numberOfFiles
    caseCountByDiagnosis { group count }
    caseCountByBreed     { group count }
    caseCountByStudyType { group count } } }
""")["searchCases"]

print(land["numberOfCases"], "cases total")             # 1029
for g in land["caseCountByDiagnosis"][:5]:
    print(g["count"], g["group"])
# 567 Osteosarcoma / 116 Bladder Cancer / 85 Lymphoma / 81 Glioma / 36 Urothelial Carcinoma
for g in land["caseCountByBreed"][:3]:
    print(g["count"], g["group"])
# 221 Mixed Breed / 104 Labrador Retriever / 88 Golden Retriever
```

## Step 2 — narrow with facet args (lists; same value OR'd, facets AND'd)

Now constrain. `searchCases` returns the post-filter counts (`filterCaseCountBy*`) so you can see what's
left to refine, plus the matching `caseIds` / `sampleIds` / `fileIds` (full arrays, not paged).

```python
cohort = icdc("""
{ searchCases(diagnosis: ["Osteosarcoma"], sex: ["Male"]) {
    numberOfCases numberOfSamples numberOfFiles
    caseIds
    fileIds
    filterCaseCountByStudyCode { group count }
    filterCaseCountByBreed     { group count } } }
""")["searchCases"]

print(cohort["numberOfCases"], "male osteosarcoma cases across",
      len(cohort["filterCaseCountByStudyCode"]), "studies")
case_ids = cohort["caseIds"]
file_ids = cohort["fileIds"]
```

## Step 3 — pull the rows (paged; default `first: 10`, so set it)

`caseOverview` takes the **same facet args** and returns flat case rows. Loop `offset` for the full set.

```python
def all_cases(**facets):
    rows, off, size = [], 0, 100
    while True:
        q = ("{ caseOverview(%s first: %d offset: %d order_by: \"case_id\" sort_direction: \"ASC\") "
             "{ case_id study_code breed sex age disease_site stage_of_disease } }")
        args = " ".join(f'{k}: {v!r}'.replace("'", '"') for k, v in facets.items())
        page = icdc(q % (args, size, off))["caseOverview"]
        rows += page
        if len(page) < size:
            return rows
        off += size

cases = all_cases(diagnosis=["Osteosarcoma"], sex=["Male"])
print(len(cases), "rows")          # 309 male osteosarcoma cases
print(cases[0])
# {'case_id': 'COTC021-0103', 'study_code': 'COTC021', 'breed': 'Bernese Mountain Dog',
#  'sex': 'Male', 'age': 6.8, 'disease_site': 'Bone (Appendicular)', 'stage_of_disease': 'Not Determined'}
```

Use `sampleOverview` / `fileOverview` the same way for sample- and file-level rows (`fileOverview`
also accepts `case_ids`, `sample_ids`, `file_uuids`).

## Step 4 — hand off to files / analysis

The `fileIds` from Step 2 feed straight into a download manifest:

```python
manifest_csv = icdc('{ createManifest(uuid: %s) }' % str(file_ids).replace("'", '"'))["createManifest"]
open("cohort_manifest.csv", "w").write(manifest_csv)
```

Then load `cohort_manifest.csv` into the Cancer Genomics Cloud. See
[files_and_download.md](files_and_download.md).

## Notes

- Facet args are **lists** even for one value: `breed: ["Boxer"]`, not `breed: "Boxer"`.
- The 18 facet dimensions are in [../references/SEARCH.md](../references/SEARCH.md). `caseCountBy*` =
  whole-repository landscape; `filterCaseCountBy*` = after your current filter.
- For a field not present in the flat `*ES` rows, switch to node queries
  ([../references/ENTITIES.md](../references/ENTITIES.md)).
