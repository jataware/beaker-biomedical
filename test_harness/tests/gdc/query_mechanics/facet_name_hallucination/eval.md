# Expect

**Expected result (verified ground truth):**
- `diagnoses.tumor_stage` → 200, no `aggregations`, `warnings.facets =
  "unrecognized values: [diagnoses.tumor_stage]"`.
- `diagnoses.ajcc_pathologic_stage` over `cases.project.project_id in ["TCGA-KIRC"]` (537 cases) →
  **stage i 270, stage iii 125, stage iv 83, stage ii 60**, plus minor substages
  (stage ib 2, stage ia 1, stage iiia 1, stage iiib 1) and **`_missing` 3**. Stage keys are lowercase.
**Pass:** uses (or self-corrects to) `diagnoses.ajcc_pathologic_stage`, reports the four main stages
with counts in the right ballpark; if it first tried `tumor_stage`, it noticed `warnings.facets` and
fixed the field rather than reporting an empty result.

# Failure Cases

**Trap(s):**
1. Faceting on `diagnoses.tumor_stage` (a TCGA-era hallucination) and reporting an empty/zero
   breakdown because the agent never inspected `warnings`.
2. Treating the 200 response as success and silently returning nothing.
**Fail:** reports 0/empty for `tumor_stage`; ignores `warnings`; or invents a stage distribution.

# Automated Checks

```yaml
checks:
  - substring: "ajcc_pathologic_stage"
  - set_contains:
      name: "stages"
      members: ["stage i", "stage ii", "stage iii", "stage iv"]
  - number:
      name: "stage_i_count"
      target: 270
      tolerance_percent: 15
  - number:
      name: "stage_iv_count"
      target: 83
      tolerance_percent: 15
  - behavior: "used diagnoses.ajcc_pathologic_stage (or inspected warnings.facets after tumor_stage failed), did not report an empty breakdown"
  - must_not_contain: ["no staging data", "stage breakdown is empty", "0 cases per stage"]
```
