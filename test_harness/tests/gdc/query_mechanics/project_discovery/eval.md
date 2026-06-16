# Expect

**Expected result (verified ground truth):**
- Filter `primary_site in ["Kidney"]`, `facets=project.project_id`, `size=0`.
- **16 projects, 2436 kidney cases total.** Top buckets:
  **TARGET-WT 652** (largest), **TCGA-KIRC 537**, **FM-AD 408**, **TCGA-KIRP 291**, **CPTAC-3 261**,
  **TCGA-KICH 113**, TARGET-RT 61, MP2PRT-WT 52, TARGET-NBL 25, TARGET-CCSK 13, HCMI-CMDC 11, …
- Faceting `disease_type` over the same filter returns lowercase keys
  (`adenomas and adenocarcinomas` 1498, `complex mixed and stromal neoplasms` 733, …); the title-case
  string returns 0 cases.
**Pass:** enumerates the project set via a `/cases` project facet, reports ≥ 10 projects, names
TARGET-WT (or at minimum a non-TCGA project) as the largest, and reports per-project counts in the
right ballpark.

# Failure Cases

**Trap(s):**
1. Returning only `TCGA-KIRC` (or "TCGA-KIRC/KIRP/KICH") and defaulting to TCGA. The largest kidney
   project is **TARGET-WT** (Wilms tumor), not a TCGA project.
2. (Sub-point) Filtering `disease_type = "Clear Cell Renal Cell Carcinoma"` (title case) returns **0** —
   GDC's `disease_type` vocabulary is lowercase and ICD-O-style (`adenomas and adenocarcinomas`,
   `complex mixed and stromal neoplasms`), not clinical subtype names.
**Fail:** returns only TCGA project(s); reports a single number; or (sub-point) silently reports 0 for
the title-case `disease_type` and stops instead of discovering the lowercase vocabulary.

# Automated Checks

```yaml
checks:
  - set_contains:
      name: "discovered_projects"
      members: ["TARGET-WT", "TCGA-KIRC", "FM-AD", "CPTAC-3"]
  - count_at_least:
      name: "projects"
      min: 10
  - number:
      name: "total_kidney_cases"
      target: 2436
      tolerance_percent: 15
  - number:
      name: "TARGET_WT_cases"
      target: 652
      tolerance_percent: 15
  - number:
      name: "TCGA_KIRC_cases"
      target: 537
      tolerance_percent: 15
  - substring: "TARGET-WT"
  - behavior: "faceted /cases by project.project_id with a primary_site=Kidney filter (discover-then-query), did NOT assume a single project"
  - must_not_contain: ["only TCGA", "kidney cancer is exclusively in TCGA"]
```
