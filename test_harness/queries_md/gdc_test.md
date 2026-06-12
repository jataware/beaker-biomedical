# GDC skill — live-harness evaluation queries

Natural-language tasks for evaluating the `genomic-data-commons` (GDC) skill in a live agent harness.
Each targets a high-value capability, embeds a trap a skill-less agent falls into, and has a
machine-gradeable outcome. Ground truth was verified against the live REST API
(`https://api.gdc.cancer.gov`) on **2026-06-11**, against **Data Release 45.0 (2025-12-04)** (confirmed
via `GET /status`). The API is fully open-access — none of these queries need a token. The harness has
Python but **no `requests` package**; the agent should use `urllib.request` and POST
`application/json`.

Counts drift with each data release — re-verify against `/status` + a `facets`/`/analysis` re-run if a
number has shifted. The *behaviors* being graded (right endpoint, right filter slot, right
interpretation) are stable; `number` checks grade tolerance/order-of-magnitude, not exact equality.

These queries deliberately avoid the entities used in the skill's own `examples/` (breast / TCGA-BRCA,
ER status, leukemia discovery, BRCA1 BAM slicing, MYC, kidney's VHL/PBRM1 top-mutated worked example).
A passing run must show the skill *generalizes*, not pattern-matches the worked examples.

---

## Query 1 — Project discovery for a site (don't default to TCGA)

**Prompt:**
> Which GDC projects contain kidney cancer cases, and how many cases are in each?

**Evaluates:** the discover-then-query workflow — facet `/cases` by `project.project_id` using a
`primary_site` filter — rather than assuming a single TCGA project. Also tests value casing: a
follow-up on `disease_type` must use the lowercase GDC vocabulary.

**Trap(s):**
1. Returning only `TCGA-KIRC` (or "TCGA-KIRC/KIRP/KICH") and defaulting to TCGA. The largest kidney
   project is **TARGET-WT** (Wilms tumor), not a TCGA project.
2. (Sub-point) Filtering `disease_type = "Clear Cell Renal Cell Carcinoma"` (title case) returns **0** —
   GDC's `disease_type` vocabulary is lowercase and ICD-O-style (`adenomas and adenocarcinomas`,
   `complex mixed and stromal neoplasms`), not clinical subtype names.

**Expected result (verified ground truth):**
- Filter `primary_site in ["Kidney"]`, `facets=project.project_id`, `size=0`.
- **16 projects, 2436 kidney cases total.** Top buckets:
  **TARGET-WT 652** (largest), **TCGA-KIRC 537**, **FM-AD 408**, **TCGA-KIRP 291**, **CPTAC-3 261**,
  **TCGA-KICH 113**, TARGET-RT 61, MP2PRT-WT 52, TARGET-NBL 25, TARGET-CCSK 13, HCMI-CMDC 11, …
- Faceting `disease_type` over the same filter returns lowercase keys
  (`adenomas and adenocarcinomas` 1498, `complex mixed and stromal neoplasms` 733, …); the title-case
  string returns 0 cases.

**Pass:** enumerates the project set via a `/cases` project facet, reports ≥ 10 projects, names
TARGET-WT (or at minimum a non-TCGA project) as the largest, and reports per-project counts in the
right ballpark.
**Fail:** returns only TCGA project(s); reports a single number; or (sub-point) silently reports 0 for
the title-case `disease_type` and stops instead of discovering the lowercase vocabulary.

**Checks (machine-gradeable):**
- `set_contains: discovered_projects ⊇ {TARGET-WT, TCGA-KIRC, FM-AD, CPTAC-3}`
- `count_at_least: projects ≥ 10`
- `number: total_kidney_cases ≈ 2436 (±15%)`
- `number: TARGET_WT_cases ≈ 652 (±15%)`
- `number: TCGA_KIRC_cases ≈ 537 (±15%)`
- `substring: "TARGET-WT"` (the largest project must appear)
- `behavior: faceted /cases by project.project_id with a primary_site=Kidney filter (discover-then-query), did NOT assume a single project`
- `must_not_contain: ["only TCGA", "kidney cancer is exclusively in TCGA"]`

---

## Query 2 — Mutation-frequency denominator (FLAGSHIP)

**Prompt:**
> What are the most frequently mutated genes in colon adenocarcinoma (TCGA-COAD), and what fraction of
> cases carry KRAS, TP53, and APC mutations?

**Evaluates:** `/analysis/top_mutated_genes` with the Portal-matching recipe — **cohort in
`case_filters`** (sets the denominator `num_cohort_ssm_cases`), **Cancer Gene Census in `filters`**
(`genes.is_cancer_gene_census = "true"`, which gates eligibility, not rank). Tests that the agent (a)
puts the cohort in the right filter slot and (b) applies the census default AND states it explicitly
(the skill makes this notice mandatory).

**Trap(s):**
1. Putting the cohort in `filters` instead of `case_filters`. The denominator then stays at the
   GDC-wide total (**18289**) and frequencies collapse to nonsense (APC reads **1.68%** instead of
   ~72%). Never divide a cohort numerator by `num_gdc_ssm_cases`.
2. Applying the Cancer Gene Census default silently, or not applying it at all. The skill requires the
   agent to say the list is census-only and that it can be lifted.

**Expected result (verified ground truth):**
- Correct recipe (`case_filters` = `cases.project.project_id in ["TCGA-COAD"]`, `filters` =
  `genes.is_cancer_gene_census = "true"`):
  - Denominator `num_cohort_ssm_cases` = **428** (COAD cases tested for SSM).
  - **APC 307/428 = 71.7%**, **TP53 237/428 = 55.4%**, **KRAS 184/428 = 43.0%**,
    MUC16 144/428 = 33.6%, PIK3CA 125/428 = 29.2%, FAT4 26.4%.
- Wrong recipe (cohort in `filters`): denominator = **18289**, APC = **1.68%** (nonsense).

**Pass:** uses `top_mutated_genes` with the cohort in `case_filters`; reports KRAS ≈ 43%, TP53 ≈ 55%,
APC ≈ 72% against a denominator of ~428; and explicitly states the result is Cancer-Gene-Census-only
(Portal default) and can be lifted.
**Fail:** reports sub-2% frequencies (the 18289-denominator collapse); reports raw counts with no
denominator; or never mentions the census restriction.

**Checks (machine-gradeable):**
- `number: cohort_denominator ≈ 428 (±10%)`
- `number: APC_pct ≈ 72% (±8 pp)`
- `number: TP53_pct ≈ 55% (±8 pp)`
- `number: KRAS_pct ≈ 43% (±8 pp)`
- `substring_all: ["APC", "TP53", "KRAS"]`
- `substring_any: ["cancer gene census", "gene census", "census", "census-only"]` (must state the default)
- `behavior: scoped the COAD cohort in case_filters and put genes.is_cancer_gene_census="true" in filters (NOT cohort in filters)`
- `must_not_contain: ["1.68%", "1.7%", "18289", "18,289"]` (the wrong-denominator artifacts)

---

## Query 3 — "Highly expressed" means most variably expressed

**Prompt:**
> What are the most highly expressed genes in lung adenocarcinoma (TCGA-LUAD)?

**Evaluates:** that the agent interprets "highly/most expressed" the way the GDC Data Portal does —
**most _variably_ expressed**, ranked by the standard deviation of `log2(uqfpkm)` via
`POST /gene_expression/gene_selection` with `gene_type = "protein_coding"` — and that it *says* it is
reporting variability, not absolute level.

**Trap(s):**
1. Interpreting "highly expressed" as absolute/median expression level (which would surface
   housekeeping genes), or pulling `/gene_expression/values` and ranking by mean.
2. Using the wrong endpoint, or not disclosing that the ranking is by variability.

**Expected result (verified ground truth):**
- `gene_selection` (cohort = `cases.project.project_id in ["TCGA-LUAD"]`, `gene_type=protein_coding`,
  `selection_size=10`) returns, sorted by stddev descending:
  **PGC, SFTPC, BPIFA1, SFTPA1, SFTPA2, SCGB3A1, S100P, SCGB3A2, FGG, SPINK1** — lung-characteristic
  surfactant/secretory genes. The response is wrapped in a `gene_selection` key with per-gene
  `symbol`, `log2_uqfpkm_stddev`, `log2_uqfpkm_median`.
- The top gene by variability (PGC, stddev ≈ 3.63) does **not** have the highest median — SFTPA2
  (median ≈ 8.89) and SFTPA1 (median ≈ 8.66) are far higher in absolute level — confirming the ranking
  is by variability, not level.

**Pass:** calls `/gene_expression/gene_selection` (protein-coding), returns a list dominated by the
lung-specific genes above, AND explicitly states the ranking is by expression *variability* (Portal
behavior), offering absolute level as a different computation.
**Fail:** returns a housekeeping/ubiquitous-gene list, claims to report absolute expression level
without caveat, or invents an endpoint.

**Checks (machine-gradeable):**
- `set_contains: top_genes ⊇ {SFTPC, SFTPA1, SFTPA2}` (surfactant genes among the top hits)
- `substring_any: ["SFTPC", "SFTPA1", "SFTPA2", "PGC", "SCGB3A2"]`
- `count_at_least: genes_returned ≥ 5`
- `substring_any: ["variab", "standard deviation", "stddev", "most variably expressed"]` (must disclose variability framing)
- `behavior: called /gene_expression/gene_selection with gene_type=protein_coding (ranked by stddev), not absolute-level from /gene_expression/values`
- `must_not_contain: ["absolute abundance", "absolute expression level"]` (unless explicitly offered as the alternative)

---

## Query 4 — Survival: log-rank requires an array of filters

**Prompt:**
> Do male and female pancreatic cancer (TCGA-PAAD) patients differ in overall survival? Give me the
> p-value.

**Evaluates:** `POST /analysis/survival` semantics — a **single** `filters` object yields one KM curve
and **no** p-value (`overallStats: {}`), whereas an **array** of two `filters` (one per group) yields
the two curves plus the log-rank `overallStats.pValue`. Also tests that the agent reads the actual
p-value rather than inventing one, and interprets it correctly (not significant).

**Trap(s):**
1. Passing one `filters` object (or asking for the whole cohort) and then inventing/​fabricating a
   p-value — there is none in that response (`overallStats` is empty).
2. Reporting a significant difference. p ≈ 0.37 is **not** significant; claiming the groups differ is
   wrong.

**Expected result (verified ground truth):**
- Array of two filters — `[gender=male AND project=TCGA-PAAD, gender=female AND project=TCGA-PAAD]`:
  `overallStats` = **pValue ≈ 0.366**, **chiSquared ≈ 0.817**, **degreesFreedom = 1**; group donor
  counts **male 101 / female 83**.
- A single `filters` object (TCGA-PAAD only) → one curve of **184** donors, `overallStats: {}` (no
  p-value).
- **Time axis is in days, not years.** Each donor's `time` is days from the index date (`time` ranges
  ~4 to ~2741 here, median ≈ 467); a correct answer that mentions follow-up/survival durations must
  state the unit is **days** (~2741 days ≈ 7.5 years, not 2741 years).

**Pass:** builds an **array** of two group filters, reports p ≈ 0.37 (read from
`overallStats.pValue`), and states the difference is **not statistically significant**.
**Fail:** passes a single filter and fabricates a p-value; claims a significant survival difference; or
reports `overallStats` is empty without realizing it needs the two-group array form.

**Checks (machine-gradeable):**
- `number: pValue ≈ 0.37 (±0.10)`
- `number: male_n ≈ 101 (±5)`
- `number: female_n ≈ 83 (±5)`
- `substring_any: ["not significant", "no significant", "not statistically significant", "no statistically significant"]`
- `substring: "days"` (the survival `time` axis is in days, not years — the agent must state the unit)
- `behavior: passed an array of two filters objects to /analysis/survival to obtain overallStats.pValue (NOT a single filters object)`
- `must_not_contain: ["statistically significant difference", "significantly different", "p < 0.05"]`

---

## Query 5 — Facet-name hallucination (200, not 400)

**Prompt:**
> Break the TCGA-KIRC cases down by tumor stage.

**Evaluates:** that the agent uses the canonical facet field and inspects `warnings` on facet calls.
The intuitive-sounding `diagnoses.tumor_stage` is **invalid** — but GDC returns HTTP **200** with **no
`aggregations` key** and `warnings.facets: "unrecognized values: [diagnoses.tumor_stage]"`, not a 400.
The correct field is `diagnoses.ajcc_pathologic_stage`.

**Trap(s):**
1. Faceting on `diagnoses.tumor_stage` (a TCGA-era hallucination) and reporting an empty/zero
   breakdown because the agent never inspected `warnings`.
2. Treating the 200 response as success and silently returning nothing.

**Expected result (verified ground truth):**
- `diagnoses.tumor_stage` → 200, no `aggregations`, `warnings.facets =
  "unrecognized values: [diagnoses.tumor_stage]"`.
- `diagnoses.ajcc_pathologic_stage` over `cases.project.project_id in ["TCGA-KIRC"]` (537 cases) →
  **stage i 270, stage iii 125, stage iv 83, stage ii 60**, plus minor substages
  (stage ib 2, stage ia 1, stage iiia 1, stage iiib 1) and **`_missing` 3**. Stage keys are lowercase.

**Pass:** uses (or self-corrects to) `diagnoses.ajcc_pathologic_stage`, reports the four main stages
with counts in the right ballpark; if it first tried `tumor_stage`, it noticed `warnings.facets` and
fixed the field rather than reporting an empty result.
**Fail:** reports 0/empty for `tumor_stage`; ignores `warnings`; or invents a stage distribution.

**Checks (machine-gradeable):**
- `substring: "ajcc_pathologic_stage"` (the correct field name)
- `set_contains: stages ⊇ {stage i, stage ii, stage iii, stage iv}`
- `number: stage_i_count ≈ 270 (±15%)`
- `number: stage_iv_count ≈ 83 (±15%)`
- `behavior: used diagnoses.ajcc_pathologic_stage (or inspected warnings.facets after tumor_stage failed), did not report an empty breakdown`
- `must_not_contain: ["no staging data", "stage breakdown is empty", "0 cases per stage"]`

---

## Query 6 (optional) — Open vs controlled access

**Prompt:**
> For the TCGA-PAAD project, how many files can I download without a token, and how many require
> controlled access?

**Evaluates:** the `files.access` field (`open` = no token; `controlled` = needs `X-Auth-Token` +
dbGaP authorization) and the open-access model. Tests that the agent splits a project's files by
`access` rather than assuming everything is open or everything needs a token.

**Trap(s):**
1. Claiming all GDC data is open (or all requires a token).
2. Reporting only the total file count without the open/controlled split.

**Expected result (verified ground truth):**
- `cases.project.project_id in ["TCGA-PAAD"]`, facet/filter on `files.access`:
  **open ≈ 4971**, **controlled ≈ 7882**, total **≈ 12853**. Open files (clinical, derived expression,
  masked SSM, …) download with no token; controlled files (BAMs/aligned reads under a dbGaP `acl`)
  need a token + project authorization.

**Pass:** reports both counts (open ~4971, controlled ~7882) with the right interpretation — open is
token-free, controlled needs auth.
**Fail:** says all files are open / all are controlled; or returns only the total.

**Checks (machine-gradeable):**
- `number: open_files ≈ 4971 (±15%)`
- `number: controlled_files ≈ 7882 (±15%)`
- `substring_all: ["open", "controlled"]`
- `behavior: filtered files by files.access (open vs controlled) for TCGA-PAAD`
- `must_not_contain: ["all files are open", "everything requires a token", "all data requires controlled access"]`

---

## Automated grading

Each per-query **Checks** bullet is tagged with one check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap's wrong answer).
- `regex` — a pattern the answer (or a returned ID) must match.
- `number` — a named numeric value with tolerance: `±N%` (counts), `±N` (small integers), `±N pp`
  (percentage points). Counts grade order-of-magnitude / within tolerance, not exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (which
  endpoint, which filter slot, which interpretation), not just prose.

**Drift caveat:** all `number` values were live-verified on **2026-06-11** against **GDC Data Release
45.0**, and they move with each data release. Grade `number` checks by tolerance/order-of-magnitude,
not exact equality; re-baseline against `GET /status` plus a fresh `facets` / `/analysis` re-run if a
value has shifted. The graded *behaviors* (correct endpoint, correct filter slot, correct
interpretation, inspecting `warnings`) are stable across releases.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Project discovery (don't default to TCGA) | ✓ | | | | | |
| Value/vocabulary casing (`disease_type` lowercase) | ✓ | | | | | |
| Mutation freq: `case_filters` vs `filters` denominator | | ✓ | | | | |
| Cancer Gene Census default + mandatory notice | | ✓ | | | | |
| "Highly expressed" = most variable (`gene_selection`) | | | ✓ | | | |
| Survival: array-of-filters log-rank vs single curve | | | | ✓ | | |
| Statistical interpretation (p≈0.37 not significant) | | | | ✓ | | |
| Facet-name validity + `warnings` inspection | | | | | ✓ | |
| `files.access` open vs controlled / no-auth model | | | | | | ✓ |
