# CTDC skill — live-harness evaluation queries

Five natural-language tasks for evaluating the `clinical-translational-data-commons` skill in a live
agent harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into, and
has a machine-gradeable outcome.

**Endpoint:** `https://clinical.datacommons.cancer.gov/v1/graphql/` (trailing slash) — a **single
GraphQL endpoint, POST-only**. There is no REST API and no GET.
**Auth:** none. All CTDC metadata/search is open-access. The API serves metadata only; file *bytes* are
fetched out-of-band via CRDC DRS / the Cancer Genomics Cloud.
**Request-body quirk:** the JSON body **MUST include a `variables` key** (even `{}`). Omitting it is a
hard error (HTTP 400, `Cannot invoke "java.util.Map.keySet()" because "variables" is null`) — *not* an
empty result. Sibling Bento commons don't require this.
**Errors:** GraphQL query errors come back **HTTP 200 with an `errors` array** (the variables error is
the exception — it 400s); always inspect `errors`.

**Data verified:** CTDC currently holds **1 study — CMB ("CM Biobank"), 248 participants, 1,140
specimens, 2,033 files, 42 targeted therapies**. Ground-truth values were confirmed against the live
API on **2026-06-11**. CTDC is early/small and counts will drift as the study set grows — re-verify
against `searchParticipants` (the live "totals" call) if numbers shift; the *behaviors* being graded
are stable.

The `requests` package is not installed in this harness; the verification used `python3` +
`urllib.request`. The skill's worked examples use `requests` — either library is acceptable as long as
the body carries the `variables` key.

> These queries deliberately use entities that appear **nowhere** in the skill's `examples/`:
> the examples work Plasma Cell Myeloma, Non-Small Cell Lung Carcinoma + Osimertinib, and Melanoma +
> Nivolumab/Pembrolizumab/Dabrafenib (participant MSB-00205), and download DICOM/Radiology-Imaging
> files. These tests use **Colorectal Carcinoma**, **Bevacizumab/Panitumumab**, **carcinogen
> exposure**, and **Variant Call Files (vcf)** instead — a passing run demonstrates the skill
> *generalizes*, not pattern-matches.

---

## Query 1 — First call: the `variables` quirk, totals, and `GroupCount.subjects`

**Prompt:**
> How many participants are in CTDC, and what's the race breakdown?

**Evaluates:** the three first-call rules in one shot — POST-only, the **required `variables` key**, and
the faceted-layer count field being **`subjects`, not `count`** (`GroupCount { group subjects }`).
`searchParticipants` with no filter is the live "totals" call.

**Traps:**
1. Sending the body **without a `variables` key** → HTTP 400 `Cannot invoke "java.util.Map.keySet()"`,
   which an agent may misread as "endpoint down" instead of "add `variables: {}`".
2. Asking for `count` inside the facet bucket → `Validation error (FieldUndefined@... Field 'count' in
   type 'GroupCount' is undefined)`. The field is **`subjects`**.

**Expected result (verified ground truth):**
- **248 participants** (1 study; also 1,140 specimens, 2,033 files, 42 targeted therapies).
- Race (`participantCountByRace`, per-participant, sums to 248): **White 188, Black or African American
  44, Asian 6, Unknown 4, Not Reported 3, American Indian or Alaska Native 2, Native Hawaiian or other
  Pacific Islander 1.**

**Pass:** reports 248 participants and a race breakdown led by White (~188) and Black or African
American (~44), having used `subjects` (not `count`) and a body with the `variables` key.
**Fail:** reports the endpoint as broken after the missing-`variables` 400, uses `count` and gives up on
the FieldUndefined error, or invents a breakdown.

**Checks (machine-gradeable):**
- `number`: total_participants ≈ 248 (±2)
- `number`: race_white ≈ 188 (±10%)
- `number`: race_black ≈ 44 (±10%)
- `substring_all`: ["white", "black or african american", "asian"]
- `behavior`: request body included a `variables` key (even `{}`)
- `behavior`: read the facet count from the `subjects` field, not `count`
- `must_not_contain`: ["endpoint is down", "service unavailable", "api is offline"]

---

## Query 2 — Fresh disease cohort + its targeted therapies (controlled vocabulary)

**Prompt:**
> Build a cohort of CTDC participants with Colorectal Carcinoma and show their targeted therapies.

**Evaluates:** the cohort-builder loop — filter `searchParticipants(ctep_disease_term: [...])`, read the
post-filter `filterParticipantCountByTargetedTherapy` buckets — on a disease and drugs the examples
never touch. Facet args are **lists** even for one value.

**Trap:** `ctep_disease_term` is a **controlled vocabulary of exact strings**. A near-miss like
`"Colorectal Cancer"` or `"colorectal carcinoma"` (wrong case) returns an **empty cohort (0
participants) with NO error** — the agent must discover the exact term from the facet landscape, not
hardcode a guess, and must not report "CTDC has no colorectal data."

**Expected result (verified ground truth):**
- Exact term **`Colorectal Carcinoma` = 50 participants** (246 specimens, 447 files; sex 25 F / 25 M).
- Targeted therapies actually received by that colorectal cohort
  (`filterParticipantCountByTargetedTherapy`): **Bevacizumab 33, Not Reported 8, Panitumumab 7,
  Regorafenib 4, Cetuximab 3, Atezolizumab 2,** then Afatinib / Encorafenib / "Encorafenib + Cetuximab"
  / Nivolumab / Pembrolizumab each **1**. (Bevacizumab and Panitumumab — anti-VEGF / anti-EGFR
  colorectal drugs — dominate, as expected; none of the examples' melanoma/myeloma drugs lead here.)

**Pass:** finds the exact term `Colorectal Carcinoma`, reports ~50 participants, and lists Bevacizumab
as the leading targeted therapy (with Panitumumab/Regorafenib/Cetuximab also present).
**Fail:** reports 0 / "no colorectal data" after a wrong-vocab guess, or returns the whole-study
therapy ranking (Bortezomib/Lenalidomide/Pembrolizumab) instead of the colorectal-scoped one.

**Checks (machine-gradeable):**
- `number`: colorectal_participants ≈ 50 (±3)
- `number`: bevacizumab_in_cohort ≈ 33 (±15%)
- `set_contains`: cohort_targeted_therapies ⊇ {Bevacizumab, Panitumumab}
- `substring`: "colorectal carcinoma"
- `behavior`: applied the `ctep_disease_term` filter (cohort-scoped) before reading therapies
- `must_not_contain`: ["no colorectal", "0 participants", "not present in ctdc"]
- `must_not_contain`: ["Bortezomib", "Lenalidomide"]  # whole-study leaders, not the colorectal cohort's

---

## Query 3 — Carcinogen-exposure facet (a CTDC-distinctive dimension)

**Prompt:**
> How many CMB participants have a recorded carcinogen exposure?

**Evaluates:** a facet dimension unique to a clinical/translational commons —
`participantCountByCarcinogenExposure` (or the `carcinogen_exposure` filter arg). Per-participant
counts.

**Trap:** the value vocabulary is `Yes` / `No` / `Unknown` / blank — **not** `Exposed`/`true`/`1`. A
wrong value (e.g. `carcinogen_exposure: ["Exposed"]`) returns **0 with no error**. Also: the agent must
read the **`Yes` bucket** for "have a recorded exposure," not the `Unknown` bucket (the largest) or a
sum.

**Expected result (verified ground truth):**
- `participantCountByCarcinogenExposure` (sums to 248): **Yes 25, No 90, Unknown 125, blank 8.**
- "Have a recorded carcinogen exposure" = the **Yes** bucket = **25 participants**
  (`searchParticipants(carcinogen_exposure: ["Yes"]) → numberOfParticipants 25`). A good answer also
  notes that 125 are Unknown (status not recorded), so "recorded as exposed" ≠ "not unexposed."

**Pass:** reports **25** participants recorded as exposed (`Yes`), and ideally contextualizes the 90 No
/ 125 Unknown / 8 blank split.
**Fail:** returns 0 after a wrong vocabulary value, or reports the Unknown count (125) / the No count
(90) as the "exposed" answer.

**Checks (machine-gradeable):**
- `number`: carcinogen_exposure_yes ≈ 25 (±3)
- `number`: carcinogen_exposure_unknown ≈ 125 (±10%)
- `substring`: "25"
- `behavior`: used the `Yes` bucket / `carcinogen_exposure: ["Yes"]`, not `Unknown` or a sum
- `must_not_contain`: ["125 participants have a recorded", "90 participants were exposed"]

---

## Query 4 — The bracketed-string array quirk on `*Overview` rows

**Prompt:**
> List the Colorectal Carcinoma participants with their targeted therapies as a clean list.

**Evaluates:** `participantOverview` row retrieval (same facet args as `searchParticipants`, plus
paging; **default `first: 10`** — must set it / loop `offset`), and the signature CTDC quirk that
**multi-valued `*Overview` fields are returned as bracketed STRINGS, not JSON arrays.**

**Trap:** `targeted_therapy` comes back as a Python `str` like `"[Cetuximab, Bevacizumab]"`, and
`anatomical_collection_site` / `tissue_category` likewise (the latter often with an empty leading or
middle element, e.g. `"[Metastatic, , Primary]"`). The agent must **parse the string** (strip `[]`,
split on `", "`) to produce a clean list — treating it as an already-parsed array, JSON-decoding it, or
printing the raw `"[...]"` is the failure.

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
**Fail:** prints raw `"[...]"` strings, treats a single-drug string as a character list, crashes
JSON-parsing the bracketed string, or returns only 10 rows assuming that's the whole cohort.

**Checks (machine-gradeable):**
- `count_at_least`: colorectal_rows ≥ 45
- `set_contains`: MSB-01627_therapies ⊇ {Cetuximab, Bevacizumab}
- `substring_any`: ["MSB-01627", "MSB-01771", "MSB-00952"]
- `behavior`: parsed the bracketed `targeted_therapy` string into a list (stripped `[]`, split on `, `)
- `behavior`: paged past the default `first: 10` to retrieve the full ~50-row cohort
- `must_not_contain`: ["[Cetuximab, Bevacizumab]"]  # the raw unparsed bracketed string verbatim

---

## Query 5 — Specimen/file counts are NOT participant counts; files download via DRS

**Prompt:**
> How many specimens of a given type are in CMB, and how do I download the data files?

**Evaluates:** two structural facts. (1) **Specimen/file facet counts are per-specimen / per-file, not
per-participant** — `specimenCountBySpecimenType` and `dataFileCountByDataFileType` sum **above** the
248-participant total because one participant has many specimens/files. (2) **The API never streams
bytes** — files carry a CRDC **DRS id** (`dg.4DFC/<uuid>`, with a `drs_uri`) you resolve out-of-band
(CRDC DRS / Cancer Genomics Cloud); `FileOverview` has **no** `signedUrl`/`url`/download field, and
`data_file_location` is often `null` (it's null for all 1,864 imaging files).

**Expected result (verified ground truth):**
- `specimenCountBySpecimenType` (per-specimen, sums to **1,140** ≫ 248): **Streck Blood to VARI 344,
  EDTA Blood 341, FFPE Block 140, Formalin Fixed Tissue 65, Bone Marrow Aspirate 56, …** A given type
  like **EDTA Blood = 341 specimens** (drawn from 234 participants) — the 341 is specimens, not
  patients.
- `dataFileCountByDataFileType` (per-file, sums to **2,033**): **Radiology Imaging 1,864 (DICOM),
  Variant Call File 85 (vcf), Variant Report 84 (pdf).**
- A real file row (`fileOverview(data_file_type: ["Variant Call File"], first: 1)`):
  `data_file_name = "MSB-00140-06-somatic-mutations-CTDCv1"`, `data_file_format = "vcf"`,
  `data_file_uuid = "dg.4DFC/CC00EEF6-1730-40B3-9FA6-3D8FCD39EB83"`,
  `drs_uri = "drs://nci-crdc.datacommons.io/dg.4DFC/CC00EEF6-1730-40B3-9FA6-3D8FCD39EB83"`.
  **Download = resolve that DRS id** (e.g.
  `POST https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/<dg.4DFC/...>/access/s3` → signed URL) or
  load the uuid set into a Cancer Genomics Cloud manifest. The CTDC GraphQL API itself returns no bytes.

**Pass:** states the specimen-type count as **specimens** (e.g. ~341 EDTA Blood / ~1,140 total
specimens), explicitly distinct from the 248 participants; produces a real `dg.4DFC/<uuid>` DRS id; and
explains download is via DRS resolution / CGC, not a direct API call.
**Fail:** reports a specimen-type or file count as a number of patients; claims the API/GraphQL endpoint
directly downloads the files; or invents a `signedUrl`/download URL field on the file record.

**Checks (machine-gradeable):**
- `number`: total_specimens ≈ 1140 (±5%)
- `number`: edta_blood_specimens ≈ 341 (±10%)
- `number`: vcf_files ≈ 85 (±15%)
- `regex`: returned DRS id matches `(?i)dg\.4DFC/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}`
- `substring_any`: ["drs://nci-crdc.datacommons.io", "ga4gh/drs", "cancer genomics cloud", "CGC"]
- `behavior`: described specimen/file counts as per-specimen/per-file, distinct from the 248 participants
- `must_not_contain`: ["341 participants", "341 patients", "1140 participants", "1140 patients"]
- `must_not_contain`: ["downloaded the file via the api", "graphql endpoint returns the file bytes", "signedUrl"]

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (this is how the trap's wrong answer is encoded).
- `regex` — a pattern the answer (or an ID it returns) must match, e.g. the DRS shape
  `(?i)dg\.4DFC/<uuid>`.
- `number` — a named numeric value with a tolerance (`±N` absolute for small integers, `±N%` for
  counts, `±N pp` for percentages).
- `set_contains` — the answer's enumerated set must include these members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace, not just
  prose (e.g. used `subjects` not `count`; paged past `first: 10`; parsed the bracketed string; included
  the `variables` key).

**Drift caveat:** all counts/IDs were live-verified on **2026-06-11** against CTDC's single GraphQL
endpoint, and move as the (currently single-study, 248-participant) commons grows. `number` checks
therefore grade **order-of-magnitude / tolerance, not exact equality** — re-baseline against
`searchParticipants` (the live totals + facet-counts call) if a value has shifted. The graded
**behaviors** (POST + `variables` key, `GroupCount.subjects`, controlled-vocab discovery, bracketed-
string parsing, per-specimen-vs-per-participant counting, DRS-based download) are stable across releases.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|:--:|:--:|:--:|:--:|:--:|
| POST-only + required `variables` key + HTTP-200/400 errors | ✓ | | | | |
| `searchParticipants` totals (live "numberOf*") | ✓ | ✓ | | | ✓ |
| `GroupCount.subjects` not `count` | ✓ | ✓ | ✓ | | ✓ |
| Cohort build by `ctep_disease_term` + filter facet counts | | ✓ | | ✓ | |
| Controlled-vocabulary exact strings (wrong value → empty, not error) | | ✓ | ✓ | | |
| Carcinogen-exposure facet (clinical/translational-distinctive) | | | ✓ | | |
| `participantOverview` rows + paging past `first: 10` | | | | ✓ | |
| Bracketed-string array quirk (parse, don't index) | | | | ✓ | |
| Specimen/file counts per-specimen/per-file ≠ per-participant | | | | | ✓ |
| File DRS id (`dg.4DFC/<uuid>`) + DRS/CGC download, no API bytes | | | | | ✓ |
| Open-access / no-auth model | ✓ | ✓ | ✓ | ✓ | ✓ |
