# Expect

**Traps:**
1. Describing values as *absolute* abundance instead of relative log2 ratios vs a common reference.
2. Letting QC/reference pseudo-cases (e.g. `QC5`, `sample_type = "Not Reported"`; or `Cell Lines`)
   into the tumor/normal split — they *are* present in `biospecimenPerStudy`, so a "drop the unmapped"
   filter does **not** remove them.
3. Mishandling the matrix syntax (it takes no GraphQL subfield selection).
**Expected result (verified ground truth):**
- **CA9 is higher in tumor.** Median `log2_ratio`: **tumor ≈ +0.49** (n = 110 Primary Tumor) vs
  **normal ≈ −1.65** (n = 84 Solid Tissue Normal). Clear, large separation.
- Answer frames the value as a **relative** log2 ratio (against the study's common reference), not an
  absolute amount.
**Pass:** concludes CA9 is higher in tumor, with the relative-ratio framing, QC channels excluded.
Bonus: mentions `log2_ratio` vs `unshared_log2_ratio`.

# Failure Cases

**Fail:** wrong direction, calls it absolute abundance, or QC/reference channels pollute the comparison.

# Automated Checks

```yaml
checks:
  - behavior: "concluded CA9 is HIGHER in tumor than adjacent/solid-tissue normal"
  - number:
      name: "tumor_median_log2_ratio"
      target: 0.49
      tolerance_absolute: 0.4
  - number:
      name: "normal_median_log2_ratio"
      target: -1.65
      tolerance_absolute: 0.5
  - number:
      name: "tumor_n"
      target: 110
      tolerance_percent: 10
  - number:
      name: "normal_n"
      target: 84
      tolerance_percent: 10
  - substring_any: ["log2 ratio", "log2_ratio", "relative", "common reference"]
  - behavior: "dropped QC/reference channels by sample_type (e.g. QC5 / \"Not Reported\" / Cell Lines), NOT by an \"unmapped\" filter"
  - must_not_contain: ["absolute abundance", "absolute amount", "absolute level"]
  - substring_any: ["unshared_log2_ratio"]
```
