# GC (General Commons) skill — live-harness evaluation queries

Five natural-language tasks for evaluating the `general-commons` (GC, formerly CDS) skill in a live
agent harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into, and
has a machine-gradeable outcome.

**These are not the skill's examples.** They deliberately avoid the entities the `examples/` use — the
pancreatic/PDAC CPTAC proteomics file set (`phs001287`, JHU TMT11 `.gct`), the Glioblastoma faceted
cohort, and the KF-ESGR Ewing-sarcoma discovery study (`phs001228`) — so a passing run demonstrates the
skill *generalizes* rather than pattern-matching the worked examples.

**Endpoint:** `https://general.datacommons.cancer.gov/v1/graphql/` — a single GraphQL endpoint (the
**trailing slash matters**). A GET returns the schema; POST a `{"query": "..."}` body for real work (no
`variables` key needed). **Auth:** none — all GC metadata/search is open-access. The API returns
**metadata only; it never downloads data bytes.**

**Verified live on 2026-06-11**, GraphQL schema `3.1.0`, data model `11.0.4`, data release `12.0.0`
("2026 May Released GC data"): **9 programs, 89 studies, 120,867 subjects, 109,535 samples, 615,790
files**. `programList`: CCDI 16, TCIA-RADIOLOGY 35, DCCPS 20, Kids First 7, PDXNet 4, HTAN 2, CPTAC 1,
MP2PRT 1, NCIcaNano 1.

**Counts drift with each data release** — `number` checks below grade order-of-magnitude / tolerance,
not exact equality. Re-baseline against the metrics queries (`numberOfStudies` / `numberOfSubjects` /
the per-study `*Count` queries) if a value has shifted.

Things every query exercises (the GC footguns): GC returns **HTTP 200 even on errors** — inspect
`errors`. **`first` defaults to 10** — set it or silently get 10 rows (max 10000). **Every scalar comes
back as a String** — counts and `file_size` too, so cast before arithmetic/comparison. Most per-study
queries **require `phs_accession`** (omitting it is a hard error, not an empty result), so resolve it
first via `studies`/`programs`. In the faceted layer each facet bucket's count field is **`subjects`,
not `count`** (`GroupCount { group subjects }`).

---

## Query 1 — Routing / "is GC even the right commons?" (boundary)

**Prompt:**
> I want genome-wide somatic mutation frequencies for prostate cancer — should I pull them from General
> Commons?

**Evaluates:** the skill's core mandate that **GC is a metadata fallback/mirror, not an analysis
engine**. GC can *locate* a prostate-cancer study's metadata, but it cannot compute mutation
frequencies — that is a `genomic-data-commons` (GDC) product. The agent should confirm via GC that the
relevant study is a *Genomics* study and redirect to GDC.

**Trap(s):**
1. Trying to answer the genomics question from GC (inventing a `mutationFrequency` / `ssms` / `genes`
   query — these do not exist in the GC schema).
2. Over-relying on GC because it *does* hold a prostate study, instead of routing to the specialized
   commons.

**Expected result (verified ground truth):**
- GC locates exactly one Genomics prostate study via faceted discovery:
  `searchSubjects(primary_diagnoses: ["Malignant Neoplasm Of Prostate"]) {
  filterSubjectCountByPhsAccession }` → **`phs001524`**. `studies(phs_accessions:["phs001524"])` →
  study_name *"The Genetic Basis of Aggressive Prostate Cancer, The Role of Rare Variation"*, acronym
  **CIDR Agg Prostate Cancer**, `study_data_types = ["Genomics"]`, `study_access = "Controlled"`,
  ~5,563 participants. Its `genomic_info` is submission-level sequencing metadata only (WXS / Illumina /
  GRCh37).
- GC has **no mutation-frequency capability**: `{ ssms { gene } }` and
  `{ mutationFrequency(gene:"TP53") }` both return `Validation error (FieldUndefined@...)`.
- Correct answer: **No — pull mutation frequencies from GDC (`genomic-data-commons`).** GC only tells
  you the study exists (and is Genomics), then you hand off; controlled access also needs dbGaP.

**Pass:** routes mutation frequencies to GDC; uses GC only to confirm `study_data_types = Genomics` for
a real prostate study (`phs001524`); does **not** fabricate a GC frequency query.
**Fail:** claims GC computes/returns mutation frequencies; invents a `mutationFrequency`/`ssms`/`genes`
query; stays in GC instead of redirecting.

**Checks (machine-gradeable):**
- `substring_all: ["genomic-data-commons" or "GDC", "phs001524"]` — names the right downstream commons and the located study.
- `substring_any: ["Genomics", "study_data_types"]` — used the study's data type to justify the routing decision.
- `must_not_contain: ["mutationFrequency", "ssms("]` — did not invent a GC mutation-frequency query (the trap).
- `behavior: redirected somatic-mutation-frequency analysis to GDC rather than computing it from GC (GC was used only to confirm the study is Genomics)`.
- `behavior: reported that GC returns metadata only and has no mutation-frequency field, rather than fabricating one`.

---

## Query 2 — caNanoLab: GC-only data + the non-`phs` key quirk

**Prompt:**
> What nanomaterial / nanotechnology data does General Commons have, and how do I pull its records?

**Evaluates:** recognizing genuinely **GC-only** data (a correct reason to stay in GC), and the
**non-`phs` study key** quirk. The NCIcaNano program's *caNanoLab Data* study is keyed by a DOI-style
accession **`10.17917`**, NOT a `phs######`. Its records live in the caNanoLab Data-Type nodes
(`characterizations`, `compositions`, `publications`, `protocols`, `investigators`), each requiring that
accession as `phs_accession`.

**Trap(s):**
1. Assuming the study key is a `phs######` accession (e.g. guessing `phs010017`) — a guessed key returns
   an **empty list with no error**, so the agent silently reports "no data."
2. Routing nanotech to a specialized commons (there isn't one — this is GC-native).

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
**Fail:** uses/guesses a `phs######` key; reports no nanotech data; tries to route nanotech elsewhere.

**Checks (machine-gradeable):**
- `substring_all: ["10.17917", "caNanoLab"]` — found the study and used its real DOI-style key.
- `substring_any: ["Nanotechnology", "nanomaterial"]` — identified the GC-only data type.
- `number: characterizations ≈ 1456 (±15%)` — real characterization record count.
- `number: compositions ≈ 1657 (±15%)` — real composition record count.
- `must_not_contain: ["phs010017", "phs10017"]` — did not fabricate a phs-style key.
- `behavior: queried a caNanoLab Data-Type node (characterizations/compositions/investigators/publications/protocols) keyed by phs_accession "10.17917"`.
- `behavior: kept the request in GC (recognized nanotech as GC-native) rather than redirecting to a specialized commons`.

---

## Query 3 — phs resolution + String-cast + default-10, on a fresh study

**Prompt:**
> How many participants and files does the Kids First pediatric myeloid-malignancies study (KF-MMC) have,
> and what's the total size of its files?

**Evaluates:** the full per-study Data-Type flow — resolve `phs_accession` **first** (per-study queries
require it), set `first`/loop to beat the **default-10** page, and **cast the String `file_size`**
before summing. KF-MMC (`phs002187`) is a fresh Kids First study (not an example entity).

**Trap(s):**
1. Omitting `phs_accession` on `files`/`participants` → a hard `MissingFieldArgument` error, not an
   empty result.
2. Calling `files(phs_accession: …)` with no `first` and getting only **10** of 3,342 files.
3. Summing/comparing `file_size` as a **String** (lexical) instead of casting to int → wrong total and a
   wrong "largest file."
4. Trusting the study node's `number_of_participants` (here **null**) instead of `participantsCount`.

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
**Fail:** omits `phs_accession`; reports a 10-file total; sums/compares `file_size` as strings; or reports
the null study-node participant field as the answer.

**Checks (machine-gradeable):**
- `substring: ["phs002187"]` — resolved the study's phs accession before pulling records.
- `number: participants ≈ 60 (±3)` — correct participant count via `participantsCount`.
- `number: files ≈ 3342 (±10%)` — correct file count via `filesCount`.
- `number: total_size_TB ≈ 5.9 (±20%)` — summed `int(file_size)` across all paginated files (~5–6 TB).
- `behavior: passed phs_accession to the files/participants query (did not hit a MissingFieldArgument error)`.
- `behavior: set first>10 or looped offset to retrieve all ~3342 files (not just the default 10)`.
- `behavior: cast file_size from String to int before summing/comparing (not lexical string math)`.

---

## Query 4 — Faceted cross-study search for a fresh disease (Medulloblastoma)

**Prompt:**
> Find subjects with medulloblastoma across General Commons studies and tell me which studies they're in.

**Evaluates:** the faceted-search family — `searchSubjects` for counts + facet buckets, resolving the
controlled-vocabulary diagnosis value, `GroupCount.subjects` (**not** `count`), the default-10 row cap on
`subjectOverview`, and **sanity-checking the facet-bucket quirk** (bucket totals count records and can
exceed the real subject count).

**Trap(s):**
1. Asking for `count` on a facet bucket → `FieldUndefined` (it's `subjects`).
2. Hardcoding the diagnosis string — the value is **`Medulloblastoma, NOS`** (with the comma); a
   near-miss like `"Medulloblastoma NOS"` returns **0 subjects, no error**. The vocabulary must be
   discovered from `subjectCountByPrimaryDiagnosis`.
3. Reporting a facet bucket (`subjectCountByPrimaryDiagnosis` = **12,934**) as a clean patient count.
   The real distinct-subject count for this cohort is **`numberOfSubjects` = 1,226** — the `subjects`
   field on buckets counts *records*, so bucket totals can far exceed the true subject count.
4. Calling `subjectOverview` with no `first` and reporting only 10 subjects.

**Expected result (verified ground truth):**
- `searchSubjects { subjectCountByPrimaryDiagnosis { group subjects } }` → bucket
  **`"Medulloblastoma, NOS"` = 12,934** (note: this exceeds the repository-wide 120,867 only in
  aggregate across many disease terms; the point is the per-bucket number is *record*-counted).
- `searchSubjects(primary_diagnoses: ["Medulloblastoma, NOS"])` → **`numberOfStudies` = 8**,
  **`numberOfSubjects` = 1,226** (the true distinct count), `numberOfFiles` = 12,934.
- `filterSubjectCountByPhsAccession` → 8 studies across the **CCDI** and **PDXNet** programs:
  `phs002790` (CTSMC, ~10,139 records), `phs002517` (CBTN, ~2,025), `phs001437` (PPTC, ~416),
  `phs002431` (Michigan, ~248), `phs002518` (~64), `phs002430` (CCDI-UCSF, ~21), `phs003215`
  (Texas Pediatric PDX, ~20), `phs002677` (CCDI-DFCI, ~1). Their per-study `subjects` buckets sum to
  ~12,918 — **far above the 1,226 distinct subjects**, the quirk to flag.
- `subjectOverview(primary_diagnoses:["Medulloblastoma, NOS"])` with no `first` returns **10** rows.

**Pass:** uses `searchSubjects`/`subjectOverview` with the discovered value `"Medulloblastoma, NOS"`;
reads the bucket count field as `subjects`; reports ~8 studies; reports the cohort as ~**1,226 distinct
subjects** (`numberOfSubjects`) and either avoids or explicitly flags the inflated ~12,934 bucket total.
**Fail:** asks for `count`; returns 0 from a wrong vocabulary string and gives up; reports 12,934 as the
patient count without caveat; reports only 10 subjects from an un-paged `subjectOverview`.

**Checks (machine-gradeable):**
- `substring: ["Medulloblastoma, NOS"]` — used the exact controlled-vocabulary diagnosis value.
- `number: distinct_subjects ≈ 1226 (±15%)` — reported `numberOfSubjects`, the true distinct count.
- `count_at_least: studies ≥ 6` — enumerated the multi-study spread (8 expected).
- `set_contains: studies ⊇ {phs002790, phs002517, phs001437}` — names the dominant medulloblastoma studies.
- `behavior: read facet buckets via the "subjects" field, not "count" (no FieldUndefined error)`.
- `behavior: discovered the diagnosis value from subjectCountByPrimaryDiagnosis rather than guessing (did not report 0/empty)`.
- `behavior: distinguished the record-counted bucket total (~12934) from the distinct subject count (~1226) — did not present 12934 as a clean patient count`.

---

## Query 5 — Files → DRS, no direct download (controlled access + dbGaP + CGC)

**Prompt:**
> List the files for the Kids First osteosarcoma study (KF-OS) and tell me how to download them.

**Evaluates:** the file/download model — `file_id` is a CRDC **DRS** id (`dg.4DFC/<uuid>`), there is **no
signed-URL field**, and a **Controlled** study (with a dbGaP `acl`) needs dbGaP authorization, with bytes
accessed by loading a manifest into the **Cancer Genomics Cloud (CGC) by Velsera** — never a direct
fetch from this API.

**Trap(s):**
1. Promising a direct download / a signed HTTP URL. There is **no `signedUrl`/`url` field** on `File`
   (`{ files{ signedUrl } }` → `FieldUndefined`), unlike PDC. `file_url_in_cds` here is a **controlled
   `s3://kf-study-...` path**, not a public HTTP link — accessing it still needs authorization.
2. Ignoring that the study is **Controlled** (skipping the dbGaP authorization step).
3. Treating the DRS `file_id` as an HTTP URL to GET.

**Expected result (verified ground truth):**
- `studies(phs_accessions:["phs001714"])` → KF-OS, *"Gabriella Miller Kids First Pediatric Research
  Program: An Integrated Clinical and Genomic Analysis of Treatment Failure in Pediatric Osteosarcoma"*,
  **`study_access = "Controlled"`**, **`acl = ['phs001714.c1']`**, `authz = ['/programs/phs001714.c1']`.
- `filesCount(phs_accession:"phs001714")` → **12,727** files.
- `files(...)` returns `file_id` like **`dg.4DFC/00006dc0-49b8-4c63-a0ae-3bc6886e5008`** — a GA4GH DRS
  id, not a URL. `filesInList(phs_accession:["phs001714"])` gives the manifest fields:
  `drs_uri = drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>` (e.g.
  `drs://nci-crdc.datacommons.io/dg.4DFC/a230d9b3-ac62-474b-874f-57711c17085d`) and
  **`accesses = ["Controlled"]`**.
- Correct download answer: this API does **not** download bytes. Build a manifest from
  `file_id`/`drs_uri`, obtain **dbGaP authorization** for `phs001714.c1` (controlled), then load the
  manifest into a **CGC (Velsera)** workspace to access/analyze the files in-cloud.

**Pass:** lists files showing the DRS `file_id`/`drs_uri` (`dg.4DFC/…`); states the study is Controlled
and needs **dbGaP** authorization; routes the actual access through a **CGC manifest** workflow.
**Fail:** promises a direct download or a signed URL; treats `file_id`/`drs_uri` as an HTTP link;
omits the controlled-access/dbGaP step.

**Checks (machine-gradeable):**
- `regex: dg\.4DFC/[0-9a-f-]+` — returned a CRDC DRS `file_id` of the right shape.
- `substring_any: ["drs://nci-crdc.datacommons.io", "drs_uri"]` — surfaced the DRS URI for the manifest.
- `substring_all: ["Controlled", "dbGaP"]` — flagged controlled access and the dbGaP authorization requirement.
- `substring_any: ["Cancer Genomics Cloud", "CGC", "Velsera"]` — pointed at the real (manifest/CGC) access path.
- `substring: ["phs001714"]` — used/reported the study's accession (and its `phs001714.c1` acl).
- `must_not_contain: ["signed url", "signedUrl", "direct download", "download link"]` — did not promise a direct fetch (the trap).
- `behavior: described the file_id/drs_uri as a DRS identifier resolved via a CGC manifest, not as an HTTP URL to GET`.

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap, e.g. a promised signed URL).
- `regex` — a pattern the answer (or an ID it returns) must match, e.g. the DRS shape `dg\.4DFC/[0-9a-f-]+`.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for small integers); large counts grade to order-of-magnitude / ~15–20%.
- `set_contains` — the answer's enumerated set must include these members (superset check), e.g. discovered `phs_accession`s.
- `count_at_least` — number of distinct items returned is ≥ N (e.g. studies in a cohort).
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (e.g. cast `file_size` to int; passed `phs_accession`; used `subjects` not `count`).

**Drift caveat:** all counts/IDs were live-verified on **2026-06-11** against GC data release `12.0.0`
(schema `3.1.0`, model `11.0.4`) and move with each data release. `number` checks therefore grade
order-of-magnitude / tolerance, **not** exact equality — re-baseline against the metrics queries
(`numberOfStudies` / `numberOfSubjects` / per-study `*Count`) and the faceted `subjectCountBy*` buckets
if a value has shifted. The *behaviors* being graded (routing, the non-`phs` key, String-cast,
`subjects`-not-`count`, DRS/no-direct-download) are stable.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|:--:|:--:|:--:|:--:|:--:|
| Routing / GC-is-a-fallback boundary | ✓ | | | | |
| GC-only data (caNanoLab / nanotech) | | ✓ | | | |
| Non-`phs` study key (`10.17917` DOI quirk) | | ✓ | | | |
| `phs_accession` resolution (required arg) | ✓ | ✓ | ✓ | | ✓ |
| Default-10 pagination footgun | | | ✓ | ✓ | |
| String-cast scalars (counts / `file_size`) | | | ✓ | | ✓ |
| Faceted search (`searchSubjects` + `GroupCount.subjects`) | ✓ | | | ✓ | |
| Facet-bucket-counts-records quirk (bucket ≠ distinct subjects) | ✓ | | | ✓ | |
| Files / DRS `file_id` / `drs_uri` / no direct download | | | | | ✓ |
| Controlled access / dbGaP / CGC manifest | ✓ | | | | ✓ |
| Open-access / no-auth metadata model | ✓ | ✓ | ✓ | ✓ | ✓ |
| "Don't invent fields" (schema is fixed) | ✓ | | | ✓ | ✓ |
