# Expect

**Expected result (verified ground truth):**
- Array of two filters — `[gender=male AND project=TCGA-PAAD, gender=female AND project=TCGA-PAAD]`:
  `overallStats` = **pValue ≈ 0.366**, **chiSquared ≈ 0.817**, **degreesFreedom = 1**; group donor
  counts **male 101 / female 83**.
- A single `filters` object (TCGA-PAAD only) → one curve of **184** donors, `overallStats: {}` (no
  p-value).
- **Time axis is in days, not years.** Each donor's `time` is days from the index date (`time` ranges
  ~4 to ~2741 here, median ≈ 467); a correct answer that mentions follow-up/survival durations must
  state the unit is **days** (~2741 days ≈ 7.5 years, not 2741 years).
**Pass:** builds an **array** of two group filters, reports p ≈ 0.37 (read from
`overallStats.pValue`), and states the difference is **not statistically significant**.

# Failure Cases

**Trap(s):**
1. Passing one `filters` object (or asking for the whole cohort) and then inventing/​fabricating a
   p-value — there is none in that response (`overallStats` is empty).
2. Reporting a significant difference. p ≈ 0.37 is **not** significant; claiming the groups differ is
   wrong.
**Fail:** passes a single filter and fabricates a p-value; claims a significant survival difference; or
reports `overallStats` is empty without realizing it needs the two-group array form.

# Automated Checks

```yaml
checks:
  - number:
      name: "pValue"
      target: 0.37
      tolerance_absolute: 0.1
  - number:
      name: "male_n"
      target: 101
      tolerance_absolute: 5
  - number:
      name: "female_n"
      target: 83
      tolerance_absolute: 5
  - substring_any: ["not significant", "no significant", "not statistically significant", "no statistically significant"]
  - substring: "days"
  - behavior: "passed an array of two filters objects to /analysis/survival to obtain overallStats.pValue (NOT a single filters object)"
  - must_not_contain: ["statistically significant difference", "significantly different", "p < 0.05"]
```
