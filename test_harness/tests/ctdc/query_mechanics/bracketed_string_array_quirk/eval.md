# Expect

**Expected result (verified ground truth):** for the 50-participant colorectal cohort, real rows
(ordered by `participant_id`) include:
- `MSB-00352` → `targeted_therapy = "[Panitumumab]"`
- `MSB-00952` → `targeted_therapy = "[Bevacizumab]"`
- `MSB-01627` → `targeted_therapy = "[Cetuximab, Bevacizumab]"` (a genuine 2-element bracketed string)
- `MSB-01771` → `targeted_therapy = "[Panitumumab, Bevacizumab]"`, with
  `anatomical_collection_site = "[Left Lobe Of The Liver, Blood, Sigmoid Colon]"` and
  `tissue_category = "[Metastatic, , Primary]"` (note the empty middle element)
A clean parse of `MSB-01627` yields the list `["Cetuximab", "Bevacizumab"]` (2 items), not the literal
string `"[Cetuximab, Bevacizumab]"` and not 1 item.
**Pass:** returns ~50 participant rows (paged, not just the default 10) with per-participant therapies
as **parsed lists**; multi-drug rows like `MSB-01627` show 2 distinct drugs.

# Failure Cases

**Trap:** `targeted_therapy` comes back as a Python `str` like `"[Cetuximab, Bevacizumab]"`, and
`anatomical_collection_site` / `tissue_category` likewise (the latter often with an empty leading or
middle element, e.g. `"[Metastatic, , Primary]"`). The agent must **parse the string** (strip `[]`,
split on `", "`) to produce a clean list — treating it as an already-parsed array, JSON-decoding it, or
printing the raw `"[...]"` is the failure.
**Fail:** prints raw `"[...]"` strings, treats a single-drug string as a character list, crashes
JSON-parsing the bracketed string, or returns only 10 rows assuming that's the whole cohort.

# Automated Checks

```yaml
checks:
  - count_at_least:
      name: "colorectal_rows"
      min: 45
  - set_contains:
      name: "MSB-01627_therapies"
      members: ["Cetuximab", "Bevacizumab"]
  - substring_any: ["MSB-01627", "MSB-01771", "MSB-00952"]
  - behavior: "parsed the bracketed `targeted_therapy` string into a list (stripped `[]`, split on `, `)"
  - behavior: "paged past the default `first: 10` to retrieve the full ~50-row cohort"
  - must_not_contain: ["[Cetuximab, Bevacizumab]"]
```
