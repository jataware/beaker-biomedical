# CDA data model — 7 tables

CDA flattens every CRDC repository into one harmonized model. There are **7 searchable tables**. The
column counts differ by interface (verified live, cdapython 2.1.0 / CDA March 2026 release — always
re-confirm with `columns()` / `tables()`, since releases add fields):

- **`cdapython` `columns()` → 64 searchable columns.** This is the set you can put in `match_all` /
  `match_any` filter strings.
- **REST `GET /columns/` → 105 columns.** The extra **41** are each table's linkage and key columns
  (`<table>_data_at_*`, `<table>_data_source_count`, `<table>_crdc_id`/`_id_alias`); they're filterable
  in raw REST `MATCH_ALL` but **not** in `cdapython` (see below). Per-table totals: file 11/18,
  mutation 26/33, observation 10/17, project 4/10, subject 7/14, treatment 3/10, upstream_identifiers
  3/3 (cdapython / REST). The per-table sections below give the REST totals; the *searchable in
  cdapython* subset excludes the linkage/key columns.

Two tables are **result entities** you query directly and that drive row counts: **`subject`** and
**`file`**. The other five (`observation`, `project`, `treatment`, `mutation`, `upstream_identifiers`)
are **joined in** with `add_columns='<table>.*'`.

## The cross-repository columns — REST-filterable, not cdapython-searchable

Every table carries a uniform set of linkage columns — this is how CDA records *which repository each
record came from*:

- `<table>_data_at_gc`, `<table>_data_at_gdc`, `<table>_data_at_icdc`, `<table>_data_at_idc`,
  `<table>_data_at_pdc` — **booleans**, one per data center (GC, GDC, ICDC, IDC, PDC).
- `<table>_data_source_count` — **integer**, how many data centers hold this record.

> **Important — these are filterable only at REST.** In raw REST `MATCH_ALL`,
> `subject_data_at_pdc = true` works (and ANDs cleanly to find overlap). In **`cdapython` 2.1.0 they are
> NOT searchable** — `match_all=['subject_data_at_gdc = true']` raises *"… is not a searchable CDA
> column."* In cdapython, express repository membership with the **`data_source=` argument** instead
> (`data_source='PDC'`, or `data_source=['GDC','PDC']` for AND/intersection). See
> [CROSS-REPOSITORY.md](CROSS-REPOSITORY.md). Either way, prefer this over the `upstream_source` field
> (known bug, below). (`project` has no `project_data_at_gc` *boolean* — but GC projects do exist; GC is
> simply not exposed as a `_data_at_gc` column there.)

cdapython result rows instead expose a single **`data_source`** column whose value is a **list** of the
repos holding that entity (e.g. `['GDC','PDC']`); the individual booleans are not returned.

## subject — research subjects / patients (14 at REST; 7 searchable in cdapython)

The study-independent entity. Human subjects are de-identified. One row per subject.

| column | type | nullable | notes |
|---|---|---|---|
| `subject_id` | text | no | primary key, e.g. `CCDI.689.0`, `TCGA-...` |
| `subject_crdc_id` | text | yes | CRDC-wide id |
| `species` | text | yes | `human` (103,225), `mouse` (298), `dog` (1,029), `human/mouse xenograft` (95), null (77,818) — see repo-mapping note |
| `year_of_birth` | integer | yes | |
| `year_of_death` | integer | yes | |
| `cause_of_death` | text | yes | e.g. `Cancer-Related Death` |
| `race` | text | yes | |
| `ethnicity` | text | yes | |
| `subject_data_at_{gc,gdc,icdc,idc,pdc}` | boolean | no | cross-DC linkage |
| `subject_data_source_count` | integer | no | |

Sex, vital status, diagnosis, age — the things you'd expect on a "patient" — live on **`observation`**,
not `subject` (one subject can have several observations from different studies). Add them with
`add_columns='observation.*'`.

> **`species` is repo-bound** (verified live): `dog` ⇔ ICDC (exact 1:1, 1,029 = 1,029), `mouse` is
> IDC-only (298), `human/mouse xenograft` is PDC-only (95); GC and the non-human sources are otherwise
> human/null. **Pass multi-token values UNQUOTED:** `match_all='species = human/mouse xenograft'` → 95,
> but quoting it (`"species = 'human/mouse xenograft'"`) silently returns **0**.

## observation — clinical / diagnostic events (17 at REST; 10 searchable in cdapython)

Per-observation clinical detail. **One subject → many observations** (up to ~15; different studies
describe the same person differently — `vital_status`/`diagnosis` can even differ or be null across one
subject's observations). Counts here are per-observation, not per-subject. Quantified (March 2026):
`diagnosis = Adenocarcinoma` → **15,603** observations (`column_values`), but only **11,794** matching
subjects (`summarize_subjects`) and **441,365** files (`summarize_files`) — three different denominators
for one predicate. Clinical value vocabularies and casing: see [FILTERS.md](FILTERS.md).

`age_at_observation` is **integer years** (verified: max stored = 90, min = 0; no values >120 — it's
not days). **Ages 90+ are HIPAA-masked to exactly 90** (`age_at_observation > 89` ≡ `= 90` → 49
subjects). It is **97.5% NULL** (only 4,649 of 182,465 subjects). There is **no age summary** in
`summarize_*` output — derive ranges with boundary filters. Most other clinical columns are mostly null
too (see [FILTERS.md](FILTERS.md)).

| column | type | nullable |
|---|---|---|
| `observation_id_alias` | bigint | no |
| `vital_status` | text | yes |
| `sex` | text | yes |
| `year_of_observation` | integer | yes |
| `age_at_observation` | integer | yes |
| `diagnosis` | text | yes |
| `morphology` | text | yes |
| `grade` | text | yes |
| `stage` | text | yes |
| `observed_anatomic_site` | text | yes |
| `resection_anatomic_site` | text | yes |
| `observation_data_at_{gc,gdc,icdc,idc,pdc}` | boolean | no |
| `observation_data_source_count` | integer | no |

## file — data files (18 at REST; 11 searchable in cdapython)

One row per file. **`drs_uri` is the handle you carry to a cloud workspace** (CDA does not download).

| column | type | nullable | notes |
|---|---|---|---|
| `file_id` | text | no | primary key |
| `file_crdc_id` | text | yes | |
| `file_name` | text | yes | |
| `file_description` | text | yes | |
| `drs_uri` | text | yes | GA4GH DRS URI — resolve in ISB-CGC / Velsera CGC / Terra |
| `access` | text | yes | `open` or `controlled` |
| `size` | bigint | yes | bytes |
| `format` | text | yes | stored UPPERCASE: `BAM`, `BAI`, `VCF`, `BCR XML`, … |
| `file_type` | text | yes | e.g. `CT Image Storage`, `Annotated Somatic Mutation` |
| `category` | text | yes | |
| `anatomic_site` | text | **no** | on the file row |
| `tumor_vs_normal` | text | yes | `tumor` / `normal` |
| `file_data_at_{gc,gdc,icdc,idc,pdc}` | boolean | no | cross-DC linkage |
| `file_data_source_count` | integer | no | |

## project — studies / programs (10 at REST; 4 searchable in cdapython)

All four searchable project columns (`project_id`, `project_type`, `project_name`, `project_short_name`)
filter in cdapython — not just `project_name`. **735 distinct project rows / 65 programs** (March 2026).

| column | type | nullable | notes |
|---|---|---|---|
| `project_id` | text | no | searchable; form `<DC>.<type>.<id>`, e.g. `GDC.project.TCGA-BRCA`, `GDC.program.<uuid>`, `IDC.collection.tcga_brca`, `dbGaP.study_accession.phs000178`, `GC.program.<uuid>` |
| `project_crdc_id` | text | yes | |
| `project_type` | text | no | searchable; one of `program`, `project`, `study`, `dbgap_study`, `collection` |
| `project_name` | text | no | searchable; descriptive label (short OR long, e.g. `CPTAC` / `CPTAC: Clinical Proteomic Tumor Analysis Consortium`) |
| `project_short_name` | text | no | searchable; the code, e.g. `TCGA`, `TCGA-BRCA`, `CPTAC`, `APOLLO` |
| `project_data_at_{gdc,icdc,idc,pdc}` | boolean | no | **no `_at_gc` boolean** (but GC projects DO exist) |
| `project_data_source_count` | integer | no | |

**Program vs project granularity:** the same study appears as multiple rows. `project_short_name = TCGA`
is the **program** (11,433 subjects = all of TCGA); `project_short_name = TCGA-BRCA` is one **project**
(1,098 subjects). One subject typically maps to several project rows (program → project → collection →
dbgap_study, one per data center) — read them with `add_columns='project.*', collate_results=True`
(nested `project_data` frame). `project_name = *cptac*` (substring, 3,843 subjects) catches more than
`project_short_name = CPTAC` (exact, 2,576) because PDC study titles embed "CPTAC" in long names.

> The `_at_gc` note is about the **boolean column**, which `project` lacks — but GC *is* tracked at the
> project level (77 `GC.*` project_ids; project rows carry data_source `GC`). Among the joinable-entity
> tables, `project` is the only one missing a `_data_at_gc` boolean (`upstream_identifiers` has no
> `_data_at_*` columns at all).

## treatment — therapies (10 at REST; 3 searchable in cdapython)

| column | type | nullable |
|---|---|---|
| `treatment_id_alias` | bigint | no |
| `treatment_anatomic_site` | text | yes |
| `treatment_type` | text | yes |
| `therapeutic_agent` | text | yes |
| `treatment_data_at_{gc,gdc,icdc,idc,pdc}` | boolean | no |
| `treatment_data_source_count` | integer | no |

`treatment_type` has **75 distinct values** (granular, down to e.g. `Amputation of 5th digit on RH`);
the most common are `Chemotherapy` (12,642), `Pharmaceutical Therapy, NOS` (11,429), `Radiation Therapy,
NOS` (10,686), `Surgery, NOS` (5,312), `Radiation, External Beam` (3,038) — run `column_values` for the
full set, don't assume a short controlled list. `therapeutic_agent` (370 distinct) tops out at
Paclitaxel, Cyclophosphamide, Cisplatin, Carboplatin. Same per-row vs per-subject gap as observation:
`therapeutic_agent = Cisplatin` → 1,270 treatment rows (`column_values`) but **1,168 subjects**
(`summarize_subjects`).

## mutation — somatic mutations (33 at REST; 26 searchable in cdapython) — use with caution

GDC/TCGA-derived (note `case_barcode`, `*_submitter_uuid`, MAF-style fields). **Mutation is a
join-only table — there is no `get_mutation_data`/`summarize_mutations` and no `/data/mutation` REST
endpoint** (only `subject` and `file` are result entities). Retrieve it via `add_columns='mutation.*'`
on a subject or file query (REST: `ADD_COLUMNS:["mutation.*"]` — the `.*` is required, bare `"mutation"`
→ 400).

**Why counts are unreliable — the real mechanism (verified live):** joined `mutation.*` columns come
back as the usual per-entity lists, **independently de-duplicated and not row-aligned** — for one TP53
subject `hugo_symbol` had length 13 while `chromosome` was 9, `reference_allele` 4, and `variant_type` 1
(distinct lengths {1,4,5,9,13}).
You therefore **cannot reconstruct individual variant records** (don't zip the columns) or derive
trustworthy variant/frequency counts from the join. `match_all=['hugo_symbol = TP53']` selects *subjects
who carry a TP53 mutation* (≈5,006), **not** mutation occurrences (GDC reports 1,461 distinct TP53 SSMs
/ 6,255 occurrences — different denominators). For variant-level or frequency work, locate the cohort
here and use GDC's own endpoints (`/ssms`, `/ssm_occurrences`, `/analysis/top_mutated_genes_by_project`)
via `genomic-data-commons`. (`hugo_symbol` has ≈21,989 distinct values — blocked in `column_values`
unless `force=True`.)

> **`hotspot` (boolean) is currently UNFILTERABLE.** Though `columns()` advertises it as searchable,
> any filter (`'hotspot = true'`/`false`/`1`/`NULL`) raises a server
> `InternalErrorException: psycopg2 DatatypeMismatch — UNION types boolean and text cannot be matched`
> (surfaced in cdapython as a cryptic `'NoneType' object has no attribute 'get'`). Filter text mutation
> columns instead (`'hugo_symbol = TP53'` → 5,006 works); to use `hotspot`, pull `add_columns='mutation.*'`
> and filter client-side.

Key columns: `mutation_id_alias`, `hugo_symbol`, `entrez_gene_id`, `hotspot` (bool), `ncbi_build`,
`chromosome`, `variant_type`, `reference_allele`, `tumor_seq_allele1`, `tumor_seq_allele2`, `dbsnp_rs`,
`mutation_status`, `transcript_id`, `gene`, `one_consequence`, `hgnc_id`, `primary_site`, `case_barcode`,
`case_id`, `sample_barcode_tumor`, `tumor_submitter_uuid`, `sample_barcode_normal`,
`normal_submitter_uuid`, `aliquot_barcode_tumor`, `tumor_aliquot_uuid`, `aliquot_barcode_normal`,
`matched_norm_aliquot_uuid`, plus the `mutation_data_at_*` / `mutation_data_source_count` linkage set.

## upstream_identifiers — provenance (3 columns)

The crosswalk from a CDA record back to its original ids in each repository. Add with
`add_columns='upstream_identifiers.*'` to see where a subject's data physically lives.

| column | type | nullable | notes |
|---|---|---|---|
| `upstream_source` | text | no | repository the id came from (GDC/PDC/IDC/GC/ICDC) |
| `upstream_field` | text | no | the field name in that repository |
| `upstream_id` | text | no | the value/id there |

> Note: the standalone `upstream_source` *summary field* (seen in `summarize_*` output) had a known
> record-linking bug flagged by upstream — for "which DC holds this" use `data_source=` (cdapython) /
> the `<table>_data_at_<dc>` booleans (REST). `upstream_identifiers.*` (the join) is the right tool for
> the actual ids — **but read it with `collate_results=True`.** Without collate, `upstream_source`,
> `upstream_field`, and `upstream_id` come back as three independently-sorted, different-length lists
> (verified: source len 4, id len 7 for one subject); zipping them pairs the wrong (source, id) values.
> `collate_results=True` yields a nested `upstream_identifiers_data` frame with each row's
> `(upstream_source, upstream_field, upstream_id)` correctly aligned.

## How the tables relate

- A **subject** has many **observations**, many **files**, belongs to one or more **projects**, may
  have **treatments** and **mutations**, and has **upstream_identifiers** in each source repository.
- From a **subject** query, pull related rows with `add_columns='observation.*'`, `'file.*'`,
  `'treatment.*'`, `'project.*'`, `'mutation.*'`, `'upstream_identifiers.*'`. With
  `collate_results=True`, the joined data lands in a nested, **row-aligned** column named
  **`<table>_data`** (e.g. `file_data`, `observation_data`), which you explode with
  `expand_subject_results(df, 'file_data')`.
- **`add_columns` does NOT fan rows out** — one subject stays one row, with each added column packed as a
  **list in a single cell**. The footgun is the opposite of duplication: those per-cell lists are
  **independently de-duplicated, so columns have different lengths and are NOT aligned** (e.g. 297
  `file_id`s vs 16 `format`s for one subject). **Never zip them.** `collate_results=True` + `expand_*`
  is the only way to get aligned per-item rows. See [FUNCTIONS.md](FUNCTIONS.md) and
  [examples/intersect_cohorts.md](../examples/intersect_cohorts.md).

## Data sources & freshness

The cdapython **`release_metadata()`** function (and the equivalent `GET /release_metadata/` endpoint)
reports, per table/column/source, the row count, the upstream `data_source_version`, and the
`data_source_extraction_date`. CDA itself is the `CDA` source (the harmonized aggregate). The five
upstream repositories: **GDC, PDC, IDC, GC** (General Commons, formerly **CDS** — older output may say
`CDS`), and **ICDC** (canine). The current aggregate at time of writing is the **March 2026** release
(extracted 2026-03-25). See [DISCOVERY.md](DISCOVERY.md).
