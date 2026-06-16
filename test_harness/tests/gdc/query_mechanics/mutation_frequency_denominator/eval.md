# Expect

**Expected result (verified ground truth):**
- Correct recipe (`case_filters` = `cases.project.project_id in ["TCGA-COAD"]`, `filters` =
  `genes.is_cancer_gene_census = "true"`):
  - Denominator `num_cohort_ssm_cases` = **428** (COAD cases tested for SSM).
  - **APC 307/428 = 71.7%**, **TP53 237/428 = 55.4%**, **KRAS 184/428 = 43.0%**,
    MUC16 144/428 = 33.6%, PIK3CA 125/428 = 29.2%, FAT4 26.4%.
- Wrong recipe (cohort in `filters`): denominator = **18289**, APC = **1.68%** (nonsense).
**Pass:** uses `top_mutated_genes` with the cohort in `case_filters`; reports KRAS ≈ 43%, TP53 ≈ 55%,
APC ≈ 72% against a denominator of ~428; and explicitly states the result is Cancer-Gene-Census-only
(Portal default) and can be lifted.

# Failure Cases

**Trap(s):**
1. Putting the cohort in `filters` instead of `case_filters`. The denominator then stays at the
   GDC-wide total (**18289**) and frequencies collapse to nonsense (APC reads **1.68%** instead of
   ~72%). Never divide a cohort numerator by `num_gdc_ssm_cases`.
2. Applying the Cancer Gene Census default silently, or not applying it at all. The skill requires the
   agent to say the list is census-only and that it can be lifted.
**Fail:** reports sub-2% frequencies (the 18289-denominator collapse); reports raw counts with no
denominator; or never mentions the census restriction.

# Automated Checks

```yaml
checks:
  - number:
      name: "cohort_denominator"
      target: 428
      tolerance_percent: 10
  - number:
      name: "APC_pct"
      target: 72
      tolerance_pp: 8
  - number:
      name: "TP53_pct"
      target: 55
      tolerance_pp: 8
  - number:
      name: "KRAS_pct"
      target: 43
      tolerance_pp: 8
  - substring_all: ["APC", "TP53", "KRAS"]
  - substring_any: ["cancer gene census", "gene census", "census", "census-only"]
  - behavior: "scoped the COAD cohort in case_filters and put genes.is_cancer_gene_census=\"true\" in filters (NOT cohort in filters)"
  - must_not_contain: ["1.68%", "1.7%", "18289", "18,289"]
```
