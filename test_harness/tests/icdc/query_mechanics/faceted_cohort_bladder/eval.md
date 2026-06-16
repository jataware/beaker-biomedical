# Expect

**Traps:**
1. `searchCases` returns **no row data** — the agent must call `caseOverview` (or `casesInList` with
   the `caseIds`) to actually *list* cases. Stopping at `searchCases` answers "how many" but not "list."
2. Reading `subjects` instead of `count` from the `GroupCountES` buckets (that field doesn't exist
   here → a `FieldUndefined` error or empty parse).
3. Hardcoding one study (e.g. "UBC01"). The bladder cohort spans **5 studies**, and two of them are
   *not* dedicated bladder studies (TCL01, ORGANOIDS01).
**Expected result (verified ground truth):**
- **116 Bladder Cancer cases** (`searchCases(diagnosis: ["Bladder Cancer"])` → `numberOfCases` 116,
  `numberOfSamples` 162, `numberOfFiles` 341, across **5 studies**).
- **Studies** (`filterCaseCountByStudyCode`): **UBC02 56, UBC01 34, UBC03 16, TCL01 7, ORGANOIDS01 3**.
- **Top breeds** (`filterCaseCountByBreed`): **Scottish Terrier 42, Mixed Breed 21, Beagle 11**,
  Labrador Retriever 5, … (≈29 distinct breeds).
- **Disease sites** (`filterCaseCountByDiseaseSite`): **Bladder 51, "Bladder, Urethra" 41**,
  "Bladder, Urethra, Prostate" 10, "Bladder, Prostate" 5, … (note the multi-site compound values).
- Real case rows from `caseOverview(diagnosis: ["Bladder Cancer"], first: …)` — e.g.
  `ORGANOIDS01-OR-A`, `TCL01-Bliley`, `UBC03-800-425`, `UBC01-776-675-Vm20`. `caseOverview` with
  `first: 200` returns all **116** rows.
**Pass:** reports ≈116 cases, names the multi-study span (≥3 studies, not one), gives breed and
disease-site breakdowns from the facets, and lists actual case_ids via an `*Overview`/`casesInList`.

# Failure Cases

**Fail:** reports only a count with no rows, claims one study, uses `subjects`, or invents case_ids.

# Automated Checks

```yaml
checks:
  - number:
      name: "bladder_cases"
      target: 116
      tolerance_percent: 15
  - number:
      name: "bladder_studies"
      target: 5
      tolerance_absolute: 1
  - substring_all: ["Scottish Terrier", "Bladder"]
  - set_contains:
      name: "studies"
      members: ["UBC02", "UBC01"]
  - count_at_least:
      name: "listed_case_ids"
      min: 3
  - regex:
      name: "case_id"
      pattern: '(UBC0[123]-|TCL01-|ORGANOIDS01-)\S+'
  - behavior: "fed searchCases counts/IDs into caseOverview (or casesInList) to produce rows"
  - must_not_contain: ["subjects"]
```
