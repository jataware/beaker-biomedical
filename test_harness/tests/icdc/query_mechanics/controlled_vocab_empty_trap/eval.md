# Expect

**Expected result (verified ground truth):**
- `searchCases(disease_site: ["Urinary Bladder"])` → `numberOfCases 0`, `caseIds []`, and the response
  has **no `errors`** (HTTP 200, clean empty). `caseOverview(disease_site: ["Urinary Bladder"])` → `[]`.
- The valid `caseCountByDiseaseSite` values include: **`Bladder` (51)**, **`Bladder, Urethra` (41)**,
  `Bladder, Urethra, Prostate` (10), `Bladder, Prostate` (5), `Bladder, Urethra, Vagina` (3),
  `Urethra, Prostate` (2), `Distal Urethra` (1), `Urethra` (1) — there is **no** "Urinary Bladder".
- Re-running with the real value: `searchCases(disease_site: ["Bladder"])` → **51 cases**.
- The agent should also note that *diagnosis* "Bladder Cancer" (116 cases, Q1) is the broader handle if
  the user wants all bladder-cancer cases regardless of the compound site string.
**Pass:** detects the empty result, explicitly attributes it to a wrong controlled-vocabulary value
(not absent data), discovers the real `disease_site` values, and rebuilds a non-empty cohort (≈51 for
`Bladder`, or 116 via the `Bladder Cancer` diagnosis).

# Failure Cases

**Trap:** `searchCases(disease_site: ["Urinary Bladder"])` returns **0 cases with NO `errors` key** (an
empty list is *not* an error). A skill-less agent concludes "ICDC has no bladder data" — which is
flatly wrong (Q1 shows 116 bladder cases). The agent must read `caseCountByDiseaseSite` to find the
real strings and re-run with one of them.
**Fail:** reports "ICDC has no bladder cases / no data," treats the empty list as a hard error, or never
discovers the valid facet values.

# Automated Checks

```yaml
checks:
  - number:
      name: "urinary_bladder_cases"
      target: 0
      exact: true
  - substring_any: ["Bladder, Urethra", "\"Bladder\"", "Bladder (51", "51 cases"]
  - behavior: "read caseCountByDiseaseSite to enumerate valid disease_site values before reconcluding"
  - behavior: "re-ran the query with a valid value and returned a non-empty cohort (≈51 Bladder, or 116 via diagnosis)"
  - must_not_contain: ["no bladder data", "ICDC does not have", "no such cases exist", "ICDC has no bladder"]
```
