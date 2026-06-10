---
name: cancer-data-aggregator
description: >-
  Search and cross-reference harmonized cancer metadata ACROSS all NCI CRDC repositories at once — GDC
  (genomics), PDC (proteomics), IDC (imaging), GC (general/CDS), and ICDC (canine) — from one model,
  via the `cdapython` Python package or its open REST service. Use when the user needs to: find which
  repositories hold data for a disease, project, or cohort; locate data that spans multiple commons
  (e.g. CPTAC across GDC+PDC+IDC); build a cross-modal cohort (subjects with BOTH imaging and
  sequencing, or matched tumor+normal BAMs); cross-reference subjects/files/specimens across data
  centers; search by harmonized clinical terms (diagnosis, anatomic_site, age, sex, treatment,
  mutation); or collect DRS URIs to hand files off to a cloud workspace. CDA harmonizes and LOCATES
  metadata only — it does not download files or run analyses. For deep single-repository analysis
  (gene-expression matrices, mutation frequency, survival, BAM slicing → `genomic-data-commons`;
  proteomics quantitation → `proteomic-data-commons`; DICOM imaging → the imaging-data-commons; GC-only
  data → `general-commons`), locate the data with CDA, then hand off to that commons' skill.
compatibility: >-
  Python 3.9+ with the `cdapython` package (`pip install
  git+https://github.com/CancerDataAggregator/cdapython.git@develop`), which depends on pandas. As of
  June 2026 that install resolves to **cdapython 2.1.0**, and its default endpoint is already the
  production service (`get_api_url()` → `https://cda.datacommons.cancer.gov`), so `set_api_url` is
  optional. No API key or auth required — all CDA metadata is open. The REST service
  (https://cda.datacommons.cancer.gov/) needs only `requests`. Actually downloading data files (via
  their DRS URIs) happens outside CDA in a cloud workspace, and controlled-access data still requires
  the user's dbGaP authorization there.
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# Cancer Data Aggregator (CDA)

CDA is a service of the NCI Cancer Research Data Commons (CRDC). It pulls metadata from the CRDC
repositories, then **cleans, harmonizes, and cross-references** it into one searchable model so you can
find subjects/files/specimens across data centers, discover a disease described differently at each
repository, and compile everything from a program (e.g. CPTAC) no matter where it landed.

**Data sources:** GDC (genomics), PDC (proteomics), IDC (imaging), GC (General Commons, formerly CDS),
ICDC (canine). **Primary interface:** the `cdapython` Python package. **Underneath:** an open REST
service at `https://cda.datacommons.cancer.gov/`.

## When to use CDA — and when to defer

Reach for CDA when the question is **cross-repository or "where is the data?"**:

- *Which* commons hold data for this disease / project / cohort? Does anything span several?
- Find subjects/files that appear in more than one repository (e.g. GDC subjects who also have PDC or
  IDC data); compile a program like CPTAC across GDC + PDC + IDC.
- Build a **cross-modal** cohort: subjects with both CT images and somatic-mutation files; matched
  tumor + normal BAMs; VCFs for the same patients in blood and tumor.
- Harmonized search by clinical terms across everything at once (diagnosis, anatomic_site, age, sex).
- Collect `drs_uri`s for a file set to load into a cloud workspace.

**Defer to the specialized commons' skill** once the data is located and the task is deep,
single-repository analysis CDA does not do — CDA is metadata-only:

| If the user wants… | Use |
|---|---|
| Gene-expression matrices, mutation frequency, survival curves, BAM slicing, CNV/SSM analysis | `genomic-data-commons` |
| Proteomics quantitation / PDC study tables | `proteomic-data-commons` |
| DICOM imaging series / viewers | the imaging-data-commons |
| Data that lives only in General Commons | `general-commons` |

The pattern is **locate with CDA → hand off**: CDA finds the data and yields DRS URIs; the specialized
commons (or a cloud workspace) analyzes or downloads it.

## Authentication

None. Every `cdapython` call and REST request is anonymous — all CDA metadata is open. CDA does not
download data; controlled-access *data* still needs dbGaP authorization when you later resolve its DRS
URI in a cloud workspace. See [auth.yaml](auth.yaml).

## Getting started

```bash
pip install git+https://github.com/CancerDataAggregator/cdapython.git@develop   # Python 3.9+
```

```python
from cdapython import *
get_api_url()                                        # -> https://cda.datacommons.cancer.gov (already production in 2.1.0)
set_api_url("https://cda.datacommons.cancer.gov/")   # optional; pins production explicitly
```

In cdapython 2.1.0 the client **already defaults to production**, so `set_api_url()` is optional —
call it only to be explicit or to point at a different host (the docs' notebooks sometimes use a
`cda-dev.*` host for testing). The trailing slash does **not** matter (both forms work);
`get_api_url()` shows the active endpoint. See [examples/quickstart.md](examples/quickstart.md).

## The core workflow

Think of CDA as one enormous harmonized spreadsheet: pick **columns** that hold what you care about,
then **filter rows** to the values you want. The reliable loop:

1. **`tables()`** — the 7 searchable tables.
2. **`columns(...)`** — get the **exact** column name; do not guess one (names are specific and each
   lives on a particular table). `columns(description='…')` finds a column by concept when you don't
   know its name.
3. **`column_values('col')`** — see the real, distinct values (and their exact spelling/casing) before
   you filter on them.
4. **`summarize_subjects(...)` / `summarize_files(...)`** — count-profile the matching set *before*
   pulling rows (cheap; tells you the size and the cross-repository breakdown).
5. **`get_subject_data(...)` / `get_file_data(...)`** — fetch the actual rows (one per subject / file).
6. **`intersect_subject_results(a, b)` / `expand_subject_results(df, '<col>_data')`** — combine cohorts
   (AND across separate queries) and explode collated columns.

> **Steps 1–3 are mandatory, not advisory.** Before writing *any* filter on a column or value you have
> not already confirmed this session, discover it first. Skipping to a guessed filter is the most
> common failure — e.g. wanting "deceased" patients, a tumor grade, or a specific drug and writing the
> filter from a made-up column/value name instead of running `columns(...)` / `column_values(...)` first.

Worked end-to-end: [examples/find_cohort.md](examples/find_cohort.md).

## Critical rules

- **Discover before you filter — never guess a column or value name.** Names are *not* guessable. A
  guessed **column** that doesn't exist makes the query fail; a guessed **value** with the wrong
  spelling/casing silently returns the wrong rows (a 0 or off count that looks legitimate). There are
  64 searchable columns across 7 tables (cdapython `columns()`), each on a specific table — bad guesses
  like `gender` (the column is
  `sex`), `tumor_stage` (it's `stage`), `cancer_type`/`disease` (it's `diagnosis`), or `patient_id`
  (it's `subject_id`) do not exist. **For any field you have not already confirmed this session, run
  `columns(...)` for the exact name (`columns(description='…')` finds it by concept) and
  `column_values('col')` for the value's exact spelling/casing BEFORE writing the filter.** This is the
  #1 cause of wrong results. See [references/DISCOVERY.md](references/DISCOVERY.md).
- **Prefer `cdapython` over the raw REST API.** The friendly filter strings and especially the `*`
  partial-match wildcards are **client-side features**. Raw REST `MATCH_ALL` is exact-match only
  (case-insensitive) with **no `*` or `%` wildcards** — verified: `diagnosis = *adenocarcinoma*`
  returns **0** at REST, while `diagnosis = Adenocarcinoma` returns 11,794. Use REST only for simple
  exact-value filters, the boolean linkage columns, `column_values`, `columns`, `release_metadata`, or
  when Python is unavailable. See [references/REST-API.md](references/REST-API.md).
- **CDA locates, it does not download or analyze.** Files come back with a `drs_uri`; resolve it in a
  cloud workspace (ISB-CGC, Velsera CGC, Terra/FireCloud). For analysis, hand off to the specialized
  commons' skill. See [examples/files_and_drs.md](examples/files_and_drs.md).
- **Check values before filtering.** Stored casing varies by column — `sex` is lowercase
  (`female`/`male`), `format` is uppercase (`BAM`, `BAI`), `diagnosis` is title-case (`Adenocarcinoma`).
  Run `column_values('col')` (case-insensitive) first; in `cdapython` use `*wildcards*` for partial
  matches.
- **Filter strings need spaces around the operator:** `'age_at_observation > 50'`, never
  `'age_at_observation>50'`. Operators: `< <= > >= = !=`; `NULL` matches missing; chained ranges work
  (`'70 < age_at_observation <= 80'`). See [references/FILTERS.md](references/FILTERS.md).
- **⚠️ `!=` is SILENTLY BROKEN on string/controlled-term columns — it returns the `=` set.** Verified
  live: `race != White` → 33,613 (identical to `race = White`); same for `sex`, `vital_status`,
  `diagnosis`, `format`, … The service drops the negation when compiling the controlled-term lookup.
  `!=` works only on numeric columns (`year_of_birth != 1961` is correct). To exclude a *string* value,
  enumerate the others with `match_any`, or use `'col = NULL'` logic — never trust `col != value`.
- **Wildcards `*` only work at the START/END of a value.** A `*` in the middle (`'diagnosis =
  Endo*carcinoma'`) is a hard error. And a positional `search_terms` arg with a **space is matched as a
  whole phrase** (`summarize_subjects('lung adenocarcinoma')` errors with "yielded no results") — AND
  separate words as separate args: `summarize_subjects('lung', 'adenocarcinoma')`.
- **Most clinical columns are mostly NULL — equality filters silently drop the missing majority.**
  Verified: `age_at_observation` 97.5% null, `stage` ~91%, `grade` ~95%, `vital_status` ~84%,
  `treatment_anatomic_site` ~100% null. Profile with `'col = NULL'` before trusting a cohort size.
- **`subject` and `file` are the two result entities.** Count subjects with subject queries and files
  with file queries — don't read the related-*file* total off a subject query (historically miscounted;
  use `summarize_files`/`get_file_data` for file counts).
- **For cross-repository overlap in `cdapython`, use the `data_source=` argument — NOT the
  `<table>_data_at_<dc>` booleans.** In cdapython 2.1.0 those booleans (and `<table>_data_source_count`)
  are **not searchable** — `match_all=['subject_data_at_gdc = true']` raises *"not a searchable CDA
  column."* Instead pass `data_source='GDC'` for one repo, or a **list for AND/intersection**:
  `data_source=['GDC','PDC']` → subjects present at **both** (verified: 2,345). The boolean columns DO
  work in the raw **REST** `MATCH_ALL` (`subject_data_at_gdc = true` AND `subject_data_at_pdc = true` →
  2,345) — they're a REST-only feature. Read the cross-repo Venn from the `data_source` summary, and the
  per-row `data_source` list column on result rows; avoid the `upstream_source` field (known
  record-linking bug). **Overlap is a *subject* concept — files are single-homed** (`file_data_source_count
  > 1` = 0). See [references/CROSS-REPOSITORY.md](references/CROSS-REPOSITORY.md).
- **`add_columns` packs per-entity *lists* into cells — and they are NOT row-aligned. Never zip them.**
  It does *not* fan rows out (one subject stays one row). Each added column becomes a list, but the lists
  from different columns are **independently de-duplicated**, so they have different lengths — verified:
  one subject came back with 297 `file_id`s but only 16 `format`s. Zipping `file_id`↔`format` (or
  `upstream_source`↔`upstream_id`, or any `mutation.*` columns) pairs the wrong values. To get aligned,
  one-row-per-item data you **must** pass `collate_results=True` (yields a nested, row-aligned
  `<table>_data` frame) then `expand_*_results()`. See [examples/intersect_cohorts.md](examples/intersect_cohorts.md).

## Data model — 7 tables

`subject` · `file` · `observation` (clinical: diagnosis, sex, age, stage, morphology…) · `project` ·
`treatment` · `mutation` (GDC-derived; counts unreliable — see ref) · `upstream_identifiers`.
`cdapython` `columns()` exposes **64 searchable columns**; the REST `/columns/` catalogue lists **105**
— the extra 41 are each table's `<table>_data_at_{gc,gdc,icdc,idc,pdc}` booleans,
`<table>_data_source_count`, and `<table>_crdc_id`/`_id_alias`, which are filterable **only at REST**
(in `cdapython` use `data_source=` instead). Full column lists and relationships:
[references/DATA-MODEL.md](references/DATA-MODEL.md).

## cdapython functions

| Function | Purpose |
|---|---|
| `tables()` | List searchable tables |
| `columns(table=, column=, description=, …)` | Find columns (wildcards on names; `description=` substring) |
| `column_values('col', filters=, data_source=, force=)` | Distinct values + counts for a column |
| `summarize_subjects(...)` / `summarize_files(...)` | Count-profile a result set (incl. cross-DC breakdown) |
| `get_subject_data(...)` / `get_file_data(...)` | Fetch matching rows (one per subject / file) |
| `intersect_subject_results(a, b, …)` / `intersect_file_results(...)` | AND two result sets (shared entities) |
| `expand_subject_results(df, '<col>_data')` / `expand_file_results(...)` | Explode a collated nested column to one row per item |
| `release_metadata()` | Per table/column/source release versions, extraction dates, row counts (the freshness/provenance source) |
| `set_api_url(url)` · `get_api_url()` · `cda_functions()` | Point at / read the active endpoint · list all functions |

Shared search arguments (most functions): positional `search_terms` (global keyword, case-insensitive,
AND'd), `match_all=[...]` (AND filter strings), `match_any=[...]` (OR), `match_from_file={...}` (match a
CDA column against a column in a local TSV), `data_source=` (`'GDC'`,`'IDC'`,`'PDC'`,`'GC'`,`'ICDC'`;
a **list ANDs** — entities present at *all* listed repos), `add_columns='table.*'`, `exclude_columns`,
`collate_results`, `return_data_as`, `output_file`. Full
signatures and return shapes: [references/FUNCTIONS.md](references/FUNCTIONS.md).

## REST service

Open, no auth, base `https://cda.datacommons.cancer.gov/`. Seven endpoints: `POST /data/{subject,file}`,
`POST /summary/{subject,file}`, `POST /column_values/{column}`, `GET /columns/`, `GET /release_metadata/`.
Body keys are UPPER_CASE (`SEARCH_LIST`, `MATCH_ALL`, `MATCH_SOME`, `ADD_COLUMNS`, `EXCLUDE_COLUMNS`,
`COLLATE_RESULTS`); responses page via `limit`/`offset` and `next_url`. Mind the exact-match-only
caveat above. See [references/REST-API.md](references/REST-API.md) and [examples/rest_api.md](examples/rest_api.md).

## Example usage

Smallest useful query — what's in the current release, no auth (cdapython has a `release_metadata()`
function; the REST endpoint returns the same data):

```python
from cdapython import release_metadata
release_metadata()[0]   # e.g. {'cda_table':'file','cda_column':'access','data_source':'CDA',
                        #        'data_source_version':'March 2026','data_source_extraction_date':'2026-03-25', ...}

# REST equivalent (no Python install beyond requests):
import requests
requests.get("https://cda.datacommons.cancer.gov/release_metadata/").json()["result"][0]
```

Worked examples in [examples/](examples/):

- [quickstart.md](examples/quickstart.md) — install, import, `set_api_url`, first query, REST helper.
- [find_cohort.md](examples/find_cohort.md) — `columns` → `column_values` → `summarize` → `get` for a
  clinical cohort (adenocarcinoma by age).
- [cross_repository.md](examples/cross_repository.md) — compile CPTAC across commons; find which data
  centers hold a cohort; the `data_source=` list (AND) and the `data_source` Venn.
- [intersect_cohorts.md](examples/intersect_cohorts.md) — matched tumor+normal BAMs; CT-image + mutation
  subjects; `intersect_*` + `collate_results` + `expand_*`.
- [files_and_drs.md](examples/files_and_drs.md) — `get_file_data` → `drs_uri` → manifest → cloud handoff
  (why there's no direct download).
- [handoff_to_gdc.md](examples/handoff_to_gdc.md) — tested CDA→GDC handoffs (proteogenomics, BAM slicing,
  mutation frequency): the verified `subject_id`/`file_id`→GDC keys and why each crosses to `genomic-data-commons`.
- [query_patterns.md](examples/query_patterns.md) — verified extra idioms: `match_any` OR,
  `search_terms` keyword, `treatment`/gene columns (`force=True`), `NULL` coverage, canine/ICDC and GC
  sources, CPTAC compile, and REST pagination + typed errors.
- [rest_api.md](examples/rest_api.md) — raw REST calls, pagination via `next_url`, and the
  wildcard/exact-match gotcha.

## References

- [references/FUNCTIONS.md](references/FUNCTIONS.md) — every `cdapython` function: signatures,
  arguments, return shapes, `return_data_as` options. Load when composing or debugging a call.
- [references/DATA-MODEL.md](references/DATA-MODEL.md) — the 7 tables, the 64 cdapython-searchable
  columns (vs 105 at REST), the cross-DC linkage columns, and how
  subject/observation/file/project/treatment/mutation relate. Load before choosing columns.
- [references/FILTERS.md](references/FILTERS.md) — search styles (`search_terms` vs `match_all`/`match_any`),
  filter-string grammar, wildcards, `NULL`, ranges, `data_source`, `match_from_file`. Load when building filters.
- [references/CROSS-REPOSITORY.md](references/CROSS-REPOSITORY.md) — the flagship: cdapython
  `data_source=` (list = AND) vs the REST-only `data_at_*` booleans, the per-row `data_source` column,
  the summary Venn (and its differing key formats), `intersect_*`, `upstream_identifiers`, and
  routing/handoff to specialized commons. Load for any "across repositories" task.
- [references/REST-API.md](references/REST-API.md) — the 7 endpoints, request/response schemas,
  pagination, and where REST semantics differ from `cdapython`. Load for raw HTTP use.
- [references/DISCOVERY.md](references/DISCOVERY.md) — the `tables`→`columns`→`column_values` discovery
  loop and `release_metadata`. Load when you don't yet know the right column or value.
- [references/TROUBLESHOOTING.md](references/TROUBLESHOOTING.md) — verified fixes for the common failure
  modes ("not a searchable CDA column", `summarize_*` returning `None`, `*` wildcards at REST, files
  single-homed, casing). Load when a query errors or a count looks wrong.

Upstream specs preserved verbatim in [assets/](assets/): `service_openapi.yaml` (REST OpenAPI),
`cdapython_man_pages.md` (the cdapython function docs).
