# Expect

**Expected result (verified ground truth):**
- Resolve: `studies(study_acronyms:["KF-MMC"])` → **`phs002187`**, *"Gabriella Miller Kids First
  Pediatric Research Program in Germline and Somatic Variants in Myeloid Malignancies in Children"*,
  `study_data_types ["Genomics"]`, `study_access "Controlled"`. (Note `number_of_participants` is null
  on the study node — use the count query.)
- `participantsCount(phs_accession:"phs002187")` → **60**. `filesCount(phs_accession:"phs002187")` →
  **3,342**.
- Paginating all 3,342 file rows and summing `int(file_size)` → **≈ 5.90 TB**
  (5,901,218,133,021 bytes). The largest single file is ~68 GB (68,103,798,878 bytes) — note the
  String-cast trap: lexical `max("9990636498", …)` wrongly returns ~9.99 GB.
- `files()` with no `first` returns exactly **10** rows (the default-10 footgun).
**Pass:** resolves `phs002187`, reports ~60 participants and ~3,342 files, and a summed size of the
right order of magnitude (~5–6 TB) computed by casting `file_size` to a number and paginating past 10.

# Failure Cases

**Trap(s):**
1. Omitting `phs_accession` on `files`/`participants` → a hard `MissingFieldArgument` error, not an
   empty result.
2. Calling `files(phs_accession: …)` with no `first` and getting only **10** of 3,342 files.
3. Summing/comparing `file_size` as a **String** (lexical) instead of casting to int → wrong total and a
   wrong "largest file."
4. Trusting the study node's `number_of_participants` (here **null**) instead of `participantsCount`.
**Fail:** omits `phs_accession`; reports a 10-file total; sums/compares `file_size` as strings; or reports
the null study-node participant field as the answer.

# Automated Checks

```yaml
checks:
  - substring: "[\"phs002187\"]"
  - number:
      name: "participants"
      target: 60
      tolerance_absolute: 3
  - number:
      name: "files"
      target: 3342
      tolerance_percent: 10
  - number:
      name: "total_size_TB"
      target: 5.9
      tolerance_percent: 20
  - behavior: "passed phs_accession to the files/participants query (did not hit a MissingFieldArgument error)"
  - behavior: "set first>10 or looped offset to retrieve all ~3342 files (not just the default 10)"
  - behavior: "cast file_size from String to int before summing/comparing (not lexical string math)"
```
