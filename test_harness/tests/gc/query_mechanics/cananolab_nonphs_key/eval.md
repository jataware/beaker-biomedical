# Expect

**non-`phs` study key** quirk. The NCIcaNano program's *caNanoLab Data* study is keyed by a DOI-style
accession **`10.17917`**, NOT a `phs######`. Its records live in the caNanoLab Data-Type nodes
(`characterizations`, `compositions`, `publications`, `protocols`, `investigators`), each requiring that
accession as `phs_accession`.
**Expected result (verified ground truth):**
- `studies(study_acronyms: ["caNanoLab"])` → `study_name "caNanoLab Data"`, `study_acronym
  "caNanoLab"`, **`phs_accession "10.17917"`**, `study_data_types ["Nanotechnology"]`,
  `study_access "Open"`, `number_of_participants` **null**.
- Keyed by `10.17917`, the caNanoLab nodes return real records:
  **characterizationsCount ≈ 1,456**, **compositionsCount ≈ 1,657**, **publicationsCount ≈ 308**,
  **protocolsCount ≈ 359**, **investigatorsCount = 1** (PI **Piotr Grodzinski**). Example composition:
  `Nanomaterial_Entity_Type ["Polymer"]`, `Functionalizing_Entity_Type ["Small Molecule"]`.
- A guessed `phs010017` key on `characterizations` returns `[]` (empty, no error) — proof the real key
  is required.
**Pass:** identifies nanotech as GC-only; uses the real key **`10.17917`** on a caNanoLab node
(`characterizations`/`compositions`/`investigators`/…); reports real record counts.

# Failure Cases

**Trap(s):**
1. Assuming the study key is a `phs######` accession (e.g. guessing `phs010017`) — a guessed key returns
   an **empty list with no error**, so the agent silently reports "no data."
2. Routing nanotech to a specialized commons (there isn't one — this is GC-native).
**Fail:** uses/guesses a `phs######` key; reports no nanotech data; tries to route nanotech elsewhere.

# Automated Checks

```yaml
checks:
  - substring_all: ["10.17917", "caNanoLab"]
  - substring_any: ["Nanotechnology", "nanomaterial"]
  - number:
      name: "characterizations"
      target: 1456
      tolerance_percent: 15
  - number:
      name: "compositions"
      target: 1657
      tolerance_percent: 15
  - must_not_contain: ["phs010017", "phs10017"]
  - behavior: "queried a caNanoLab Data-Type node (characterizations/compositions/investigators/publications/protocols) keyed by phs_accession \"10.17917\""
  - behavior: "kept the request in GC (recognized nanotech as GC-native) rather than redirecting to a specialized commons"
```
