# CDA data model — 7 tables, 105 columns

CDA flattens every CRDC repository into one harmonized model. There are **7 searchable tables** and
**105 columns** total (counts below are from the live `GET /columns/` endpoint — always re-confirm with
`columns()` / `tables()`, since releases add fields).

Two tables are **result entities** you query directly and that drive row counts: **`subject`** and
**`file`**. The other five (`observation`, `project`, `treatment`, `mutation`, `upstream_identifiers`)
are **joined in** with `add_columns='<table>.*'`.

## The cross-repository columns (on every table)

Every table carries a uniform set of linkage columns — this is how CDA records *which repository each
record came from*:

- `<table>_data_at_gc`, `<table>_data_at_gdc`, `<table>_data_at_icdc`, `<table>_data_at_idc`,
  `<table>_data_at_pdc` — **booleans**, one per data center (GC, GDC, ICDC, IDC, PDC).
- `<table>_data_source_count` — **integer**, how many data centers hold this record.

Filter on these (`subject_data_at_pdc = true`) to find cross-repository overlap. They are the reliable
linkage signal — prefer them over the `upstream_source` field (known bug, below). See
[CROSS-REPOSITORY.md](CROSS-REPOSITORY.md). (`project` is the one exception — it has no
`project_data_at_gc`; GC isn't tracked at the project level.)

## subject — research subjects / patients (14 columns)

The study-independent entity. Human subjects are de-identified. One row per subject.

| column | type | nullable | notes |
|---|---|---|---|
| `subject_id` | text | no | primary key, e.g. `CCDI.689.0`, `TCGA-...` |
| `subject_crdc_id` | text | yes | CRDC-wide id |
| `species` | text | yes | `human`, `mouse`, `dog`, `human/mouse xenograft` (and null) |
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

## observation — clinical / diagnostic events (17 columns)

Per-observation clinical detail. **One subject → many observations** (different studies describe the
same person differently). Counts here are per-observation, not per-subject.

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

## file — data files (18 columns)

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

## project — studies / programs (10 columns)

| column | type | nullable | notes |
|---|---|---|---|
| `project_id` | text | no | |
| `project_crdc_id` | text | yes | |
| `project_type` | text | no | |
| `project_name` | text | no | searchable, e.g. matches `*cptac*` |
| `project_short_name` | text | no | |
| `project_data_at_{gdc,icdc,idc,pdc}` | boolean | no | **no `_at_gc`** |
| `project_data_source_count` | integer | no | |

## treatment — therapies (10 columns)

| column | type | nullable |
|---|---|---|
| `treatment_id_alias` | bigint | no |
| `treatment_anatomic_site` | text | yes |
| `treatment_type` | text | yes |
| `therapeutic_agent` | text | yes |
| `treatment_data_at_{gc,gdc,icdc,idc,pdc}` | boolean | no |
| `treatment_data_source_count` | integer | no |

## mutation — somatic mutations (33 columns) — use with caution

GDC/TCGA-derived (note `case_barcode`, `*_submitter_uuid`, MAF-style fields). **The upstream docs warn
the mutation endpoint can return wrong *counts* (though correct rows) and is not fully harmonized to the
other tables.** Treat mutation counts as approximate, and prefer GDC's own analysis endpoints
(`genomic-data-commons`) for rigorous mutation-frequency work.

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
> record-linking bug flagged by upstream — for "which DC holds this" use the `<table>_data_at_<dc>`
> booleans instead. `upstream_identifiers.*` (the join) is the right tool for the actual ids.

## How the tables relate

- A **subject** has many **observations**, many **files**, belongs to one or more **projects**, may
  have **treatments** and **mutations**, and has **upstream_identifiers** in each source repository.
- From a **subject** query, pull related rows with `add_columns='observation.*'`, `'file.*'`,
  `'treatment.*'`, `'project.*'`, `'mutation.*'`, `'upstream_identifiers.*'`. With
  `collate_results=True`, the joined data lands in a nested column named **`<table>_data`** (e.g.
  `file_data`, `observation_data`), which you explode with `expand_subject_results(df, 'file_data')`.
- `add_columns` joins can **fan out rows** (one subject × many files = many rows). This is the
  documented duplication footgun — collate + expand instead of reading a raw fanned-out table. See
  [FUNCTIONS.md](FUNCTIONS.md) and [examples/intersect_cohorts.md](../examples/intersect_cohorts.md).

## Data sources & freshness

`GET /release_metadata/` reports, per table/column/source, the row count, the upstream
`data_source_version`, and the `data_source_extraction_date`. CDA itself is the `CDA` source (the
harmonized aggregate). The five upstream repositories: **GDC, PDC, IDC, GC** (General Commons, formerly
**CDS** — older output may say `CDS`), and **ICDC** (canine). See [DISCOVERY.md](DISCOVERY.md).
