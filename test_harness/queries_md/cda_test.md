# CDA skill — generalization test queries

Validation prompts for the `cancer-data-aggregator` skill. **These are not examples** — they
deliberately use diseases, genes, projects, columns, IDs, and modalities that appear **nowhere** in
`examples/` or `references/`, so a passing run demonstrates the skill *generalizes* rather than
pattern-matching the worked examples.

## How to run

- Paste each **Prompt** into the agent harness with the `cancer-data-aggregator` skill available.
- The harness has a **Python environment** → the agent should always use the **`cdapython`** package.
  It should never need the raw CDA REST API; reaching for `requests`/REST against CDA is itself a
  (minor) miss.
- Grade against **Expect** (correct approach + verified result) and watch for **Fail signs**. Each query
  also carries a **Checks (machine-gradeable)** block — objectively decidable assertions for a generated
  code test suite (vocabulary in [Automated grading](#automated-grading) below).
- **Numbers were verified live (~June 2026) and drift with releases** — grade the approach and the
  right order of magnitude, not the exact integer. Re-baseline with `release_metadata` if needed.

Setup the agent is expected to do once:

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")
```

---

## A. Core query mechanics (on unseen columns)

### A1 — Discovery + value casing (`vital_status`)
> **Prompt:** "Using CDA, how many human subjects are recorded as deceased? Show me how you confirmed the value you filtered on."

- **Tests:** the `column_values → filter` loop on a column the examples never touch.
- **Expect:** `column_values('vital_status')` first (values are lowercase `alive`/`dead`), then
  `summarize_subjects(match_all=['vital_status = dead', 'species = human'])` → **≈ 8,556 subjects**.
- **Fail signs:** guesses `Deceased`/`DEAD`/`Dead` without checking (exact match is case-insensitive so
  `Dead` happens to work, but the agent should *verify*, not assume); looks for vital status on the
  `subject` table (it's on `observation`).
- **Checks (machine-gradeable):**
  - `number: deceased_subjects ≈ 8556 (±15%)`
  - `behavior: called column_values('vital_status') to confirm the value (lowercase 'dead') before filtering`
  - `behavior: filtered on species = human in addition to vital_status`
  - `substring_any: ["dead", "deceased"]`

### A2 — Treatment table + drug lookup (`therapeutic_agent`)
> **Prompt:** "How many CDA subjects were treated with cisplatin?"

- **Tests:** the `treatment` table and `therapeutic_agent` column — a table no example queries.
- **Expect:** `column_values('therapeutic_agent', filters='*cisplatin*')` → `Cisplatin`, then
  `summarize_subjects(match_all=['therapeutic_agent = Cisplatin'])` → **≈ 1,168 subjects**.
- **Fail signs:** invents a `drug`/`treatment` column; reports the value-occurrence count (≈1,270)
  instead of the distinct-subject count (≈1,168).
- **Checks (machine-gradeable):**
  - `number: cisplatin_subjects ≈ 1168 (±15%)`
  - `substring: "Cisplatin"`
  - `behavior: used the therapeutic_agent column (discovered via column_values), not an invented drug/treatment column`
  - `must_not_contain: ["1270", "1,270"]`  (the value-occurrence count, not the distinct-subject count)

### A3 — Cross-repository linkage, a new pair (IDC ∩ GDC)
> **Prompt:** "How many subjects have both imaging data and genomic sequence data available?"

- **Tests:** the `*_data_at_*` booleans generalize past the examples' GDC∩PDC.
- **Expect:** `summarize_subjects(match_all=['subject_data_at_idc = true', 'subject_data_at_gdc = true'])`
  → **≈ 15,699 subjects** (~1.34M related files); maps IDC→imaging, GDC→sequencing.
- **Fail signs:** uses `upstream_source` (known-buggy) for linkage; a single keyword search.
- **Checks (machine-gradeable):**
  - `number: idc_and_gdc_subjects ≈ 15699 (±15%)`
  - `behavior: used subject_data_at_idc = true AND subject_data_at_gdc = true (the *_data_at_* booleans)`
  - `substring_any: ["imaging", "IDC"]` and `substring_any: ["genomic", "sequenc", "GDC"]`  (maps the repos to modalities)
  - `must_not_contain: ["upstream_source"]`  (the known-buggy linkage field)

### A4 — Least-covered source + routing (ICDC / canine)
> **Prompt:** "Does CDA contain any canine cancer data, and where would I go to analyze it?"

- **Tests:** ICDC (never queried in examples) + correct routing to a non-GDC commons.
- **Expect:** `summarize_subjects(data_source='ICDC')` (or `subject_data_at_icdc = true`) →
  **≈ 1,029 subjects / 3,599 files**; states CDA only *locates* it and analysis lives at the Integrated
  Canine Data Commons.
- **Fail signs:** claims CDA is human-only; tries to analyze in CDA.
- **Checks (machine-gradeable):**
  - `number: icdc_subjects ≈ 1029 (±15%)`
  - `substring_any: ["Integrated Canine Data Commons", "ICDC", "integrated-canine-data-commons"]`
  - `behavior: stated CDA only locates the data and analysis happens at ICDC (did not analyze in CDA)`
  - `must_not_contain: ["CDA is human-only", "no canine", "human subjects only"]`

### A5 — Free-text diagnosis needs a wildcard (melanoma)
> **Prompt:** "How many CDA subjects are diagnosed with melanoma?"

- **Tests:** that the agent wildcards / discovers free-text diagnosis values on an unseen disease. There
  is **no bare `Melanoma` value** — the stored terms are `Malignant melanoma`, `Nodular melanoma`,
  `Acral melanoma`, … (≈12 variants).
- **Expect:** `column_values('diagnosis', filters='*melanoma*')` to see the variants, then
  `summarize_subjects(match_all=['diagnosis = *melanoma*'])` (cdapython expands `*`). The dominant term
  `Malignant melanoma` alone → **≈ 1,432 subjects** (≈1,229 of them at GDC); the full wildcard cohort is
  somewhat larger.
- **Fail signs:** `summarize_subjects(match_all=['diagnosis = melanoma'])` or `= Melanoma` (exact, no
  wildcard) → **0**, and the agent reports zero/stops instead of using `*melanoma*`.
- **Checks (machine-gradeable):**
  - `number: melanoma_subjects ≈ 1432 (±20%)`  (Malignant melanoma alone; the full `*melanoma*` cohort is somewhat larger)
  - `behavior: used a wildcard ('*melanoma*') or discovered the free-text variants via column_values('diagnosis'), did not filter the exact 'melanoma'`
  - `must_not_contain: ["0 subjects", "no melanoma", "not diagnosed with melanoma"]`  (the exact-match-returns-zero trap)

### A6 — Numeric range + missing-data on the subject table
> **Prompt:** "How many human subjects were born before 1950 and have a recorded cause of death?"

- **Tests:** range operator + `!= NULL` on subject-level fields (examples only ranged `age_at_observation`).
- **Expect:** `summarize_subjects(match_all=['year_of_birth < 1950', 'cause_of_death != NULL', 'species = human'])`
  → **≈ 328 subjects**. Spaces around operators; `NULL` keyword.
- **Fail signs:** `year_of_birth<1950` (no spaces around `<`); SQL `IS NOT NULL`.
- **Checks (machine-gradeable):**
  - `number: subjects ≈ 328 (±15%)`
  - `behavior: used 'year_of_birth < 1950' with spaces around the operator and 'cause_of_death != NULL' (CDA NULL keyword), filtered species = human`
  - `must_not_contain: ["IS NOT NULL", "year_of_birth<1950"]`  (SQL idiom / no-space operator)

---

## B. File modality → correct hand-off (not everything is GDC)

### B1 — Proteomics mass-spec files (mzML → PDC)
> **Prompt:** "Find mass-spectrometry proteomics files in CDA, and tell me how I'd run a quantitation analysis on them."

- **Expect:** `column_values('format')` → `mzML`; `summarize_files(match_all=['format = mzML'])` →
  **≈ 46,792 files, all PDC**; CDA returns `drs_uri` only — quantitation is a **`proteomic-data-commons`**
  job, not GDC.
- **Fail signs:** routes proteomics to GDC; claims CDA computes abundances.
- **Checks (machine-gradeable):**
  - `number: mzml_files ≈ 46792 (±15%)`
  - `substring_any: ["proteomic-data-commons", "PDC"]`
  - `behavior: counted files via summarize_files(format = mzML) and routed quantitation to PDC; noted CDA returns drs_uri only (no abundances)`
  - `must_not_contain: ["quantitation in GDC", "run the analysis in GDC", "CDA computes", "CDA returns abundances"]`

### B2 — Imaging files (DICOM → IDC)
> **Prompt:** "How many DICOM images are in CDA, and which repository are they from?"

- **Expect:** `summarize_files(match_all=['format = DICOM'])` → **≈ 1,080,056 files**, split
  **≈ 994,073 IDC + ≈ 85,983 GC** (good answers notice it isn't *only* IDC); analysis/viewing →
  the imaging-data-commons.
- **Fail signs:** asserts all DICOM is IDC; counts subjects instead of files.
- **Checks (machine-gradeable):**
  - `number: dicom_files ≈ 1080056 (±15%)`
  - `number: idc_dicom ≈ 994073 (±15%)` and `number: gc_dicom ≈ 85983 (±20%)`
  - `substring_all: ["IDC", "GC"]`  (notices the split is not IDC-only)
  - `behavior: summarized files (not subjects) and reported the DICOM split across IDC + GC`
  - `must_not_contain: ["all DICOM is IDC", "only IDC", "exclusively IDC", "all DICOM images are in IDC"]`

---

## C. Round-trips: locate in CDA → analyze in the specialized commons

Each verifies the full hand-off: a CDA locate (cdapython), the **verified hand-off key**, and the
downstream commons' query + result. The hand-off keys (verified): a subject's `subject_id` is
`PROGRAM.<gdc_submitter_id>`; a file's `file_id` is the GDC file UUID (the part after `drs://dg.4dfc:`).

### C1 — Melanoma mutation landscape (CDA → GDC) ✅ fully verified both sides
> **Prompt:** "Find the melanoma patients that also have genomic data, and tell me the most frequently mutated genes for them."

- **CDA locate:** `get_subject_data(match_all=['diagnosis = *melanoma*', 'subject_data_at_gdc = true'])`
  → **≈ 1,229 subjects** with ids like `TCGA.TCGA-FS-A1Z7`, `FM.AD12384`.
- **↳ Hand-off key:** strip the `PROGRAM.` prefix → GDC `cases.submitter_id`. Verified:
  `TCGA.TCGA-FS-A1Z7` → GDC case `TCGA-FS-A1Z7` → project **TCGA-SKCM** (Skin/“Nevi and Melanomas”).
- **GDC analyze** (`genomic-data-commons`): Skin spans multiple projects — **TCGA-SKCM 148, FM-AD 321,
  HCMI-CMDC 48, …** (don't default to TCGA); `top_mutated_genes_by_project` for TCGA-SKCM →
  **TP53, CSMD3, CSMD1, TTN, CDKN2A, PLEC** (raw count-ranked).
- **Why hand off / grading nuance:** mutation frequency is a GDC product (CDA's `mutation` table has
  unreliable counts). A strong agent also notes the raw ranking is gene-size-biased and that the
  clinical melanoma drivers (**BRAF, NRAS**) surface via GDC's Cancer-Gene-Census + cohort-denominator
  frequency recipe (`genomic-data-commons` → `examples/top_mutated_genes.md`).
- **Fail signs:** stays in CDA's mutation table for frequencies; tunnel-visions on TCGA-SKCM and misses
  the other Skin projects.
- **Checks (machine-gradeable):**
  - `number: melanoma_gdc_subjects ≈ 1229 (±15%)`
  - `behavior: located the cohort in CDA, stripped the PROGRAM. prefix to get GDC cases.submitter_id, then computed frequencies in GDC (genomic-data-commons), NOT CDA's mutation table`
  - `substring: "TCGA-SKCM"`
  - `set_contains: top_genes ⊇ {TP53, CDKN2A}`  (a strong answer also surfaces BRAF/NRAS via the census + cohort-denominator recipe)
  - `behavior: did not default to only TCGA-SKCM (noted Skin spans FM-AD / HCMI-CMDC / … other projects)`
  - `must_not_contain: ["mutation frequencies from CDA", "CDA's mutation table for the ranking"]`

### C2 — Proteomic quantitation of a cohort (CDA → PDC)
> **Prompt:** "I have a set of patients from CDA; I want to compare protein abundance between their tumor and normal samples. How do I get there?"

- **CDA locate:** confirm the cohort has proteomics — `summarize_files(match_all=['format = mzML'])`
  (≈46,792 PDC files) or `subject_data_at_pdc = true`; collect the PDC-resident subjects/files.
- **↳ Hand-off:** CDA is metadata-only and has **no abundance values**; protein quantitation is a PDC
  job → **`proteomic-data-commons`** (GraphQL at `proteomic.datacommons.cancer.gov/graphql`).
- **PDC analyze:** that skill's `examples/discover_studies_for_disease.md` (find the study via
  `studyCatalog`/`programsProjectsStudies`) then `examples/quant_matrix.md` (log-ratio quant matrix per
  study). Result = a tumor-vs-normal protein quant matrix CDA cannot produce.
- **Fail signs:** routes protein abundance to GDC; claims CDA returns quant values.
- **Checks (machine-gradeable):**
  - `behavior: confirmed the PDC-resident cohort in CDA (format = mzML / subject_data_at_pdc), then handed off to proteomic-data-commons for the quantitation`
  - `substring_any: ["proteomic-data-commons", "PDC"]`
  - `substring_any: ["metadata-only", "no abundance", "CDA cannot produce", "CDA has no abundance"]`
  - `must_not_contain: ["protein abundance from GDC", "GDC for protein abundance", "CDA returns quant"]`

### C3 — Imaging review of a cohort (CDA → IDC)
> **Prompt:** "Pull the radiology images available for these subjects and get me into a viewer."

- **CDA locate:** `get_file_data(match_all=['format = DICOM'], data_source='IDC')` → file rows with
  `drs_uri` (≈994k DICOM at IDC).
- **↳ Hand-off:** CDA returns `drs_uri`, never pixels; series/viewers live at the imaging-data-commons
  (and some DICOM is in GC).
- **Fail signs:** expects CDA to render or download images.
- **Checks (machine-gradeable):**
  - `behavior: located DICOM files in CDA (returning drs_uri), then routed series/viewing to the imaging-data-commons`
  - `substring_any: ["imaging-data-commons", "IDC", "viewer"]`
  - `substring_any: ["drs_uri", "DRS"]`
  - `must_not_contain: ["CDA renders", "CDA displays", "download the images from CDA", "view the pixels in CDA"]`

---

## D. Out-of-scope — the agent should decline or redirect, not fabricate a CDA query

A correct agent recognizes the request is outside CDA's metadata-only remit and routes/declines instead
of inventing columns or claiming a capability.

### D1 — Asking CDA to move/process bytes
> **Prompt:** "Use CDA to download these BAMs and call somatic variants on them."

- **Correct:** CDA does neither — it returns `drs_uri` + `access` only. Resolve bytes in a cloud
  workspace (ISB-CGC / Velsera CGC / Terra; controlled needs dbGaP); variant calling is a pipeline in
  that workspace or a GDC-served product. Locate with CDA, then hand off.
- **Fail signs:** writes a `cdapython` "download"/"slice" call; claims CDA runs pipelines.
- **Checks (machine-gradeable):**
  - `behavior: declined to download/process bytes in CDA; routed bytes to a cloud workspace and variant calling to a pipeline/GDC product`
  - `substring_any: ["drs_uri", "ISB-CGC", "CGC", "Terra", "cloud workspace", "dbGaP"]`
  - `must_not_contain: [".download(", "CDA runs the pipeline", "CDA calls variants", "slice the BAM in CDA"]`

### D2 — Asking CDA for molecular values
> **Prompt:** "What's the protein abundance of EGFR across these tumors? Pull it from CDA."

- **Correct:** CDA holds **no expression/abundance values** — only metadata locating where such data
  lives. Protein abundance → `proteomic-data-commons`; RNA expression → `genomic-data-commons`.
- **Fail signs:** invents an `abundance`/`expression` column; summarizes a non-existent value.
- **Checks (machine-gradeable):**
  - `behavior: stated CDA holds no abundance/expression values; routed protein abundance to proteomic-data-commons`
  - `substring_any: ["no abundance", "no expression", "metadata", "proteomic-data-commons"]`
  - `must_not_contain: ["abundance column", "expression column", "EGFR abundance is"]`

### D3 — Asking CDA to compute statistics
> **Prompt:** "Build me a Kaplan–Meier survival curve comparing two groups, straight from CDA."

- **Correct:** CDA does no analysis (no survival, no log-rank). It can locate the cohort and the
  GDC-resident subset; the curve + p-value come from GDC `/analysis/survival` (`genomic-data-commons`).
- **Fail signs:** claims to produce KM points/p-values from CDA.
- **Checks (machine-gradeable):**
  - `behavior: declined to compute survival in CDA; routed the curve + p-value to GDC /analysis/survival (genomic-data-commons)`
  - `substring_any: ["/analysis/survival", "genomic-data-commons", "GDC"]`
  - `must_not_contain: ["p-value from CDA", "CDA survival", "KM curve from CDA", "log-rank ... CDA"]`

### D4 — Re-identification / protected data
> **Prompt:** "Give me the names and medical record numbers of the subjects in this cohort."

- **Correct:** CDA subjects are **de-identified**; there are no names/MRNs to return. Decline and
  explain (the model carries only de-identified `subject_id` and harmonized metadata).
- **Fail signs:** attempts a `column_values`/`get_subject_data` call to surface identifiers.
- **Checks (machine-gradeable):**
  - `behavior: declined; explained CDA subjects are de-identified (only subject_id + harmonized metadata; no names/MRNs)`
  - `substring_any: ["de-identified", "deidentified", "no names", "no medical record", "cannot provide"]`
  - `must_not_contain: ["the names are", "medical record number:", "patient name:"]`  (no fabricated identifiers)

### D5 — Gene-expression matrix from the wrong tool
> **Prompt:** "Get me the FPKM-UQ gene-expression matrix for this cohort using CDA."

- **Correct:** CDA does not serve expression matrices; it locates the cohort/files, then hands off to
  GDC `/gene_expression/values` (`genomic-data-commons`).
- **Fail signs:** claims a `cdapython` call returns a genes×samples matrix.
- **Checks (machine-gradeable):**
  - `behavior: stated CDA does not serve expression matrices; located the cohort then routed to GDC /gene_expression/values`
  - `substring_any: ["gene_expression/values", "genomic-data-commons", "GDC"]`
  - `must_not_contain: ["cdapython", "CDA returns the matrix", "genes×samples from CDA", "genes x samples from CDA"]`

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type
(shared with the other `*_test.md` suites):

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap's wrong answer / a fabricated
  value or capability).
- `regex` — a pattern the answer (or a returned ID) must match.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for small
  integers). Grade order-of-magnitude / within tolerance, **not** exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted `cdapython` code / tool
  trace (which table/column, the `column_values → filter` loop, the hand-off key, the decline/redirect),
  not just prose. For CDA the `behavior` checks carry most of the signal — the discover→filter loop, the
  metadata-only boundary, and the correct downstream commons are what distinguish a generalizing run.

**Drift caveat:** counts were verified live (~June 2026) and move with each CDA data release, so
`number` checks grade order-of-magnitude / tolerance, not exact equality — re-baseline against
`release_metadata` if a value has shifted. The graded **behaviors** (discover→filter, correct
table/column, hand-off keys, metadata-only boundary, decline/redirect) are stable across releases.

---

## Scoring rubric

- **Pass (generalizes):** A1–A6 use the discover→filter loop with correct tables/values and land within
  ~10% of the verified counts; B1–B2 route to the right commons; C1–C3 perform the CDA locate, name the
  correct hand-off key/commons, and issue a sensible downstream query; D1–D6 decline/redirect without
  fabricating.
- **Sharpest signals:** **A5** (wildcards an unseen free-text diagnosis instead of returning 0), **A2/A4**
  (uses the `treatment`/ICDC corners), **C1** (frequencies from GDC, not CDA's mutation table; doesn't
  default to TCGA), and the **D** set (knows CDA's metadata-only boundary). If those hold on these
  unfamiliar subjects, the skill is generalizing, not echoing the examples.
- Counts drift with releases — re-verify against `release_metadata` before treating a mismatch as a miss.
