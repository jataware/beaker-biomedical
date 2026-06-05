# Clinical diagnoses + biospecimen mapping for a study

Pull per-case diagnoses for a study and join them to the biospecimen chain so each aliquot carries its
patient's clinical context. See [../references/CLINICAL.md](../references/CLINICAL.md) for how PDC
splits clinical data across queries and which ID each one needs.

## Example

```python
import time, requests
URL = "https://proteomic.datacommons.cancer.gov/graphql"
def pdc(q, tries=5):
    for k in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=180).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        data = b.get("data")
        if data and all(v is not None for v in data.values()):
            return data
        time.sleep(2 * (k + 1))          # PDC returns transient null payloads under load
    raise RuntimeError("PDC returned null data after retries")

PDC_STUDY = "PDC000127"

# Resolve the IDs once — diagnoses query wants study_id; biospecimen wants pdc_study_id.
s = pdc('{ study(pdc_study_id: "%s") { study_id study_submitter_id } }' % PDC_STUDY)["study"][0]
study_id = s["study_id"]

# 1. Diagnoses per case (paginated). Stop on a short page — don't trust pagination.total (often null).
def all_diagnoses(study_id, page=200):
    out, offset = [], 0
    while True:
        q = '''{ paginatedCaseDiagnosesPerStudy(study_id: "%s" offset: %d limit: %d)
                 { caseDiagnosesPerStudy { case_submitter_id disease_type
                     diagnoses { primary_diagnosis tumor_grade tumor_stage ajcc_pathologic_stage morphology } } } }''' % (study_id, offset, page)
        rows = pdc(q)["paginatedCaseDiagnosesPerStudy"]["caseDiagnosesPerStudy"]
        out.extend(rows)
        offset += page
        if len(rows) < page:
            return out

dx = all_diagnoses(study_id)
dx_by_case = {c["case_submitter_id"]: c["diagnoses"] for c in dx}   # note: list per case
print(f"{len(dx_by_case)} cases with diagnoses")

# 2. Biospecimen rows: aliquot -> case (+ sample_type). One row per aliquot.
bio = pdc('''{ biospecimenPerStudy(pdc_study_id: "%s")
              { aliquot_submitter_id case_submitter_id sample_type } }''' % PDC_STUDY)["biospecimenPerStudy"]

# 3. Join: attach each aliquot's patient diagnosis.
for b in bio[:5]:
    case = b["case_submitter_id"]
    dlist = dx_by_case.get(case, [])
    primary = dlist[0]["primary_diagnosis"] if dlist else "?"
    print(f"{b['aliquot_submitter_id']:16} {case:12} {b['sample_type']:20} {primary}")
```

## Notes

- **Mind the ID type per query** (verified live): `paginatedCaseDiagnosesPerStudy` /
  `paginatedCaseDemographicsPerStudy` / `clinicalMetadata` take `study_id`;
  `paginatedCaseExposuresPerStudy` takes `study_submitter_id`; follow-ups/treatments and
  `biospecimenPerStudy` take `pdc_study_id`. Resolve all three with `study` up front.
- **One-to-many.** Each case can have several diagnoses/samples — keep them as lists, don't collapse to
  one row per case.
- **Want everything at once?** `clinicalPerStudy(pdc_study_id: …)` returns demographics + diagnoses +
  nested exposures/follow-ups/treatments/samples in a single (large, non-paginated) call — good for a
  modest study; use the paginated per-sub-entity queries for large studies or single slices.
- The same `aliquot_submitter_id` values key the quantitation matrix columns — this join is how you
  attach clinical variables to expression data ([quant_matrix.md](quant_matrix.md)).
