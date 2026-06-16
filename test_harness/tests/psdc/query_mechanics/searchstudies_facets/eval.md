# Expect

**Traps:**
1. Reporting a facet's `subjects` as a participant count (e.g. "3 biospecimen subjects", or "2 breast
   cancer patients") — here `subjects` counts **studies**.
2. Assuming biospecimen collection is rare; in fact all three studies report `biospecimen_collection =
   "Yes"`.
**Expected result (verified ground truth, 2026-06-11):**
- `numberOfStudies` = **3**, `numberOfDiagnosis` = **40**.
- `studyCountByBiospecimenCollection`: **Yes = 3** (all three studies; `subjects` = 3 **studies**).
  Filtering `searchStudies(biospecimen_collection: ["Yes"])` → `filterStudyCountByStudy` = NLST, PBCS,
  PLCO (each `subjects` = 1 study).
- `studyCountByStudyDesign`: Case-Control Study 1, Clinical Trial 1, Cohort Study - Prospective 1 (each
  = 1 study).
- `studyCountByNeoplasm`: **breast = 2 studies**, **lung = 2 studies**, Not Applicable = 3, and ~37
  single-study sites (prostate gland, colorectum, ovary, …) each = 1 study.
**Pass:** correctly reports that **all 3** studies collected biospecimens and that **breast** and
**lung** are each covered by **2 studies**, explicitly framing `subjects` as a **study** count, not a
participant count.

# Failure Cases

**Fail:** describes the facet `subjects` as numbers of people/patients, or reports the wrong study sets.

# Automated Checks

```yaml
checks:
  - number:
      name: "biospecimen_yes_studies"
      target: 3
      tolerance_absolute: 0
  - number:
      name: "breast_studies"
      target: 2
      tolerance_absolute: 0
  - number:
      name: "lung_studies"
      target: 2
      tolerance_absolute: 0
  - set_contains:
      name: "biospecimen_studies"
      members: ["NLST", "PLCO", "PBCS"]
  - substring_any: ["number of studies", "studies, not", "counts studies", "study count"]
  - must_not_contain: ["3 participants collected", "2 breast cancer patients", "2 patients with lung"]
  - behavior: "used searchStudies studyCountBy*/filterStudyCountBy* facets and interpreted subjects as a study count"
```
