# Expect

**Expected result (verified ground truth):**
- `searchSubjects { subjectCountByPrimaryDiagnosis { group subjects } }` → bucket
  **`"Medulloblastoma, NOS"` = 12,934** (note: this exceeds the repository-wide 120,867 only in
  aggregate across many disease terms; the point is the per-bucket number is *record*-counted).
- `searchSubjects(primary_diagnoses: ["Medulloblastoma, NOS"])` → **`numberOfStudies` = 8**,
  **`numberOfSubjects` = 1,226** (the true distinct count), `numberOfFiles` = 12,934.
- `filterSubjectCountByPhsAccession` → 8 studies across the **CCDI** and **PDXNet** programs:
  `phs002790` (CTSMC, ~10,139 records), `phs002517` (CBTN, ~2,025), `phs001437` (PPTC, ~416),
  `phs002431` (Michigan, ~248), `phs002518` (~64), `phs002430` (CCDI-UCSF, ~21), `phs003215`
  (Texas Pediatric PDX, ~20), `phs002677` (CCDI-DFCI, ~1). Their per-study `subjects` buckets sum to
  ~12,918 — **far above the 1,226 distinct subjects**, the quirk to flag.
- `subjectOverview(primary_diagnoses:["Medulloblastoma, NOS"])` with no `first` returns **10** rows.
**Pass:** uses `searchSubjects`/`subjectOverview` with the discovered value `"Medulloblastoma, NOS"`;
reads the bucket count field as `subjects`; reports ~8 studies; reports the cohort as ~**1,226 distinct
subjects** (`numberOfSubjects`) and either avoids or explicitly flags the inflated ~12,934 bucket total.

# Failure Cases

**Trap(s):**
1. Asking for `count` on a facet bucket → `FieldUndefined` (it's `subjects`).
2. Hardcoding the diagnosis string — the value is **`Medulloblastoma, NOS`** (with the comma); a
   near-miss like `"Medulloblastoma NOS"` returns **0 subjects, no error**. The vocabulary must be
   discovered from `subjectCountByPrimaryDiagnosis`.
3. Reporting a facet bucket (`subjectCountByPrimaryDiagnosis` = **12,934**) as a clean patient count.
   The real distinct-subject count for this cohort is **`numberOfSubjects` = 1,226** — the `subjects`
   field on buckets counts *records*, so bucket totals can far exceed the true subject count.
4. Calling `subjectOverview` with no `first` and reporting only 10 subjects.
**Fail:** asks for `count`; returns 0 from a wrong vocabulary string and gives up; reports 12,934 as the
patient count without caveat; reports only 10 subjects from an un-paged `subjectOverview`.

# Automated Checks

```yaml
checks:
  - substring: "[\"Medulloblastoma, NOS\"]"
  - number:
      name: "distinct_subjects"
      target: 1226
      tolerance_percent: 15
  - count_at_least:
      name: "studies"
      min: 6
  - set_contains:
      name: "studies"
      members: ["phs002790", "phs002517", "phs001437"]
  - behavior: "read facet buckets via the \"subjects\" field, not \"count\" (no FieldUndefined error)"
  - behavior: "discovered the diagnosis value from subjectCountByPrimaryDiagnosis rather than guessing (did not report 0/empty)"
  - behavior: "distinguished the record-counted bucket total (~12934) from the distinct subject count (~1226) — did not present 12934 as a clean patient count"
```
