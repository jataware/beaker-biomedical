# PDC skill — live-harness evaluation queries

Three natural-language tasks for evaluating the `proteomic-data-commons` skill in a live agent
harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into, and has a
gradeable outcome. Ground-truth values were verified against the live API (`https://proteomic.datacommons.cancer.gov/graphql`)
on 2026-06-05 (PDC Data Release 6.1; ~9 programs / 30 projects / 227 studies / 6,239 cases / 195,269
files). Counts may drift with future data releases — re-verify against `getPDCMetrics` if numbers
shift; the *behaviors* being graded are stable.

---

## Query 1 — Discovery ("don't assume a single study")

**Prompt:**
> What proteomics studies does PDC have for clear cell renal cell carcinoma, and how many cases does each have?

**Evaluates:** discovery workflow (`programsProjectsStudies` / `diseasesAvailable`), the no-auth/open
path, single-endpoint usage.

**Trap:** hardcoding one study ("CPTAC-3 / PDC000127"). The skill requires enumerating first.

**Expected result:**
- Returns **multiple** studies (not one), spanning **4 analytical fractions**: Proteome,
  Phosphoproteome, Glycoproteome, Metabolome (~12 studies total for `disease_type = "Clear Cell Renal
  Cell Carcinoma"` via `programsProjectsStudies`).
- Names real `pdc_study_id`s (e.g. `PDC000127`, `PDC000128`, `PDC000413`, `PDC000414`, …).
- Reports case counts (e.g. via `diseasesAvailable`: *CPTAC3 Discovery and Confirmatory* = 212 ccRCC
  cases; the `study` query reports `PDC000127` `cases_count` = 124).

**Pass:** ≥ 2 distinct studies found, correct discovery query used, real IDs + counts.
**Fail:** single study returned, invented study IDs, or only the portal/UI suggested.

**Checks (machine-gradeable):**
- `count_at_least: studies ≥ 2` (the discovery should surface ~12 across the analytical fractions)
- `set_contains: study_ids ⊇ {PDC000127}` (a strong answer also names PDC000128 / PDC000413 / PDC000414)
- `regex: returned study ids match PDC\d{6}`
- `number: PDC000127_cases ≈ 124 (±10%)` (the `study` query's `cases_count`; `diseasesAvailable` reports 212 ccRCC cases for CPTAC3 Discovery+Confirmatory)
- `substring_any: ["Proteome", "Phosphoproteome", "Glycoproteome", "Metabolome"]` (names ≥1 analytical fraction)
- `behavior: enumerated studies via a discovery query (programsProjectsStudies / diseasesAvailable), did NOT hardcode a single study`
- `must_not_contain: ["the only study", "single study", "CPTAC-3 is the one study"]`

---

## Query 2 — Quantitation flagship (relative abundance + aliquot→case mapping)

**Prompt:**
> In the CPTAC ccRCC proteome study (PDC000127), is the CA9 protein more abundant in tumor tissue than in adjacent normal tissue?

**Evaluates:** `quantDataMatrix` (un-paginated 2-D array, `data_type: "log2_ratio"`, no-subfield
syntax); parsing the `aliquot_id:aliquot_submitter_id` header; mapping aliquots → cases → `sample_type`
via `biospecimenPerStudy`; **dropping QC/reference channels by `sample_type`** (not by "unmapped").

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
**Fail:** wrong direction, calls it absolute abundance, or QC/reference channels pollute the comparison.

**Checks (machine-gradeable):**
- `behavior: concluded CA9 is HIGHER in tumor than adjacent/solid-tissue normal`
- `number: tumor_median_log2_ratio ≈ 0.49 (±0.4)` and `number: normal_median_log2_ratio ≈ -1.65 (±0.5)`
- `number: tumor_n ≈ 110 (±10%)` and `number: normal_n ≈ 84 (±10%)`
- `substring_any: ["log2 ratio", "log2_ratio", "relative", "common reference"]` (frames the value as a relative log2 ratio)
- `behavior: dropped QC/reference channels by sample_type (e.g. QC5 / "Not Reported" / Cell Lines), NOT by an "unmapped" filter`
- `must_not_contain: ["absolute abundance", "absolute amount", "absolute level"]`
- (bonus) `substring_any: ["unshared_log2_ratio"]`

---

## Query 3 — Files + download + version resolution + runtime robustness

**Prompt:**
> List the processed protein-report files for study PDC000127, download one, and verify it's intact.

**Evaluates:** resolving `pdc_study_id` → the **version-specific** `study_id` via `studyCatalog`
(`is_latest_version`); `filesPerStudy` with `signedUrl`; md5 verification; awareness of the 7-day URL
expiry and 10-downloads/IP/24h limits; and **retrying PDC's transient `null` payloads** instead of
crashing.

**Traps:**
1. Passing `pdc_study_id` where `study_id` is required, or using a stale/non-latest version UUID.
2. Treating a transient `{"data": null}` (HTTP 200, no `errors`) — or a populated result with a nested
   `pagination: null` — as a hard failure.
3. Caching/reusing an expired signed URL.

**Expected result (verified ground truth):**
- `studyCatalog(pdc_study_id: "PDC000127")` → latest version `study_id =
  dbe94609-1fb3-11e9-b7f8-0a80fada099c` (study_version 1, `is_latest_version = "yes"`).
- `filesPerStudy(study_id: …)` returns real files with a working `signedUrl { url }` (a pre-signed
  S3 link, no auth headers needed). `filesCountPerStudy` shows ~9 `file_type` × `data_category`
  combinations (e.g. *Peptide Spectral Matches / Open Standard* = 575 files).
- Downloaded file's computed md5 matches the returned `md5sum`.

**Pass:** resolves the latest `study_id`, lists real files, fetches a signed URL, and verifies the
checksum — handling at least one null/retry gracefully.
**Fail:** ID-type error, crash on a null response, or claims a successful download with no checksum check.

**Checks (machine-gradeable):**
- `substring: "dbe94609-1fb3-11e9-b7f8-0a80fada099c"` (the resolved latest version-specific `study_id`)
- `behavior: resolved pdc_study_id → version-specific study_id via studyCatalog (is_latest_version="yes"); did NOT pass pdc_study_id where study_id is required, nor a stale version UUID`
- `substring_any: ["signedUrl", "signed URL", "presigned", "s3"]` (fetched a pre-signed S3 link, no auth headers)
- `behavior: computed the downloaded file's md5 and compared it to the returned md5sum`
- `behavior: handled at least one transient null payload (HTTP 200 {"data": null} or nested pagination:null) by retrying, did not crash`
- `number: peptide_spectral_matches_open_standard_files ≈ 575 (±15%)` (a real `filesCountPerStudy` bucket)
- `must_not_contain: ["7-day URL has not expired", "reused the cached signed URL"]` (signed URLs expire in 7 days; 10 downloads/IP/24h)

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type
(shared with the other `*_test.md` suites):

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap, e.g. "absolute abundance").
- `regex` — a pattern the answer (or a returned ID) must match, e.g. a `pdc_study_id` `PDC\d{6}`.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for log2 ratios /
  small integers). Grade order-of-magnitude / within tolerance, **not** exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (the
  discovery query, the version resolution, dropping QC channels by `sample_type`, the md5 check, the
  transient-null retry), not just prose.

**Drift caveat:** counts/IDs were live-verified on **2026-06-05** against **PDC Data Release 6.1**
(`https://proteomic.datacommons.cancer.gov/graphql`) and move with each data release, so `number`
checks grade order-of-magnitude / tolerance, not exact equality — re-baseline with `getPDCMetrics` if a
value has shifted. Version-specific UUIDs (e.g. the `study_id` above) are stable identifiers; the graded
**behaviors** (discovery-not-hardcode, relative-not-absolute interpretation, version resolution, QC
filtering, md5 verification, transient-null retry) are stable across releases.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 |
|---|:--:|:--:|:--:|
| Discovery (disease → studies) | ✓ | | |
| Three study-ID flavors / version resolution | | ✓ | ✓ |
| `quantDataMatrix` + relative-not-absolute interpretation | | ✓ | |
| Aliquot → case mapping (`biospecimenPerStudy`) + QC filtering | | ✓ | |
| Files / `signedUrl` / download / expiry | | | ✓ |
| Open-access / no-auth model | ✓ | ✓ | ✓ |
| Transient-null retry / robustness | | | ✓ |
