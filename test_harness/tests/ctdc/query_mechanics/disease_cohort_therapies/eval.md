# Expect

**Expected result (verified ground truth):**
- Exact term **`Colorectal Carcinoma` = 50 participants** (246 specimens, 447 files; sex 25 F / 25 M).
- Targeted therapies actually received by that colorectal cohort
  (`filterParticipantCountByTargetedTherapy`): **Bevacizumab 33, Not Reported 8, Panitumumab 7,
  Regorafenib 4, Cetuximab 3, Atezolizumab 2,** then Afatinib / Encorafenib / "Encorafenib + Cetuximab"
  / Nivolumab / Pembrolizumab each **1**. (Bevacizumab and Panitumumab — anti-VEGF / anti-EGFR
  colorectal drugs — dominate, as expected; none of the examples' melanoma/myeloma drugs lead here.)
**Pass:** finds the exact term `Colorectal Carcinoma`, reports ~50 participants, and lists Bevacizumab
as the leading targeted therapy (with Panitumumab/Regorafenib/Cetuximab also present).

# Failure Cases

**Trap:** `ctep_disease_term` is a **controlled vocabulary of exact strings**. A near-miss like
`"Colorectal Cancer"` or `"colorectal carcinoma"` (wrong case) returns an **empty cohort (0
participants) with NO error** — the agent must discover the exact term from the facet landscape, not
hardcode a guess, and must not report "CTDC has no colorectal data."
**Fail:** reports 0 / "no colorectal data" after a wrong-vocab guess, or returns the whole-study
therapy ranking (Bortezomib/Lenalidomide/Pembrolizumab) instead of the colorectal-scoped one.

# Automated Checks

```yaml
checks:
  - number:
      name: "colorectal_participants"
      target: 50
      tolerance_absolute: 3
  - number:
      name: "bevacizumab_in_cohort"
      target: 33
      tolerance_percent: 15
  - set_contains:
      name: "cohort_targeted_therapies"
      members: ["Bevacizumab", "Panitumumab"]
  - substring: "colorectal carcinoma"
  - behavior: "applied the `ctep_disease_term` filter (cohort-scoped) before reading therapies"
  - must_not_contain: ["no colorectal", "0 participants", "not present in ctdc"]
  - must_not_contain: ["Bortezomib", "Lenalidomide"]
```
