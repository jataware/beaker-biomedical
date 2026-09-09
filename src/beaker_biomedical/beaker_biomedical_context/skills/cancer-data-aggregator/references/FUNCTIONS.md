# cdapython function reference

The current `cdapython` (**version 2.1.0** as of June 2026 — a full rewrite; the older
`Q`/`fetch_rows`/`summary_counts` APIs are retired) exposes a small set of functions. Import everything
with `from cdapython import *`. Verbatim upstream docs:
[../assets/cdapython_man_pages.md](../assets/cdapython_man_pages.md).

```python
from cdapython import *
get_api_url()      # active endpoint (already production in 2.1.0); set_api_url(...) only to change it
cda_functions()    # the authoritative function list for your installed version
```

`cda_functions()` (2.1.0) returns: `tables`, `columns`, `column_values`, `summarize_subjects`,
`summarize_files`, `get_subject_data`, `get_file_data`, `expand_subject_results`, `expand_file_results`,
`intersect_subject_results`, `intersect_file_results`, `release_metadata`, the logging helpers
(`get_valid_log_levels`, `get_log_level`, `set_log_level`, `enable/disable_console_logging`,
`enable/disable_file_logging`), `get_api_url`, `set_api_url`, and `cda_functions`.

## Shared search arguments

`summarize_subjects`, `summarize_files`, `get_subject_data`, and `get_file_data` all accept the same
querying arguments:

- **`*search_terms`** (positional strings) — **global keyword search** across all columns;
  case-insensitive; multiple terms are **AND**'d. `*` wildcards allowed. `summarize_subjects('kidney',
  'vcf')` = subjects tagged with both. (Added April 2026.)
- **`match_all=[...]`** — list of **filter strings**, **ALL** must hold (AND).
- **`match_any=[...]`** — list of filter strings, **at least one** must hold (OR).
- **`match_from_file={'input_file','input_column','cda_column_to_match'}`** — keep rows whose
  `cda_column_to_match` equals any value in `input_column` of a local TSV. Great for "I have 100 IDs,
  what else exists about them?" — see [examples/cross_repository.md](../examples/cross_repository.md).
- **`data_source=`** — restrict to upstream repositories: `'GDC'`, `'IDC'`, `'PDC'`, `'GC'`, `'ICDC'`.
  A **single** value keeps entities present at that repo; a **list ANDs** (kept only if present at
  *every* listed repo — `data_source=['GDC','PDC']` → the overlap). Default: no filter. This is the
  cdapython way to filter by repository — the `<table>_data_at_<dc>` booleans are *not* searchable here
  (REST-only). Result rows carry a `data_source` column = the per-entity list of repos.
- **`add_columns=`** — pull related columns from another table into the result. Accepts whole-table
  macros (`'observation.*'`, `'file.*'`, `'upstream_identifiers.*'`, `'mutation.*'`) or **bare** column
  names (`'diagnosis'`); a **table-qualified single column like `'observation.diagnosis'` is rejected**
  ("…which is neither" a column nor a `table.*` macro). It does **not** multiply rows — each added column
  comes back as a **list packed into one cell** per result row. ⚠️ Those per-cell lists are
  **independently de-duplicated across columns, so they are NOT row-aligned** (verified: one subject →
  297 `file_id`s but 16 `format`s). **Never zip them** to recover (id, attribute) pairs. For aligned
  one-row-per-item data, use `collate_results=True` (below) then `expand_*_results`.
- **`exclude_columns=`** — drop columns from the result.

Filter-string grammar (`'COLUMN OP VALUE'`, spaces around `OP` **required**), wildcards, `NULL`, and
ranges are documented in [FILTERS.md](FILTERS.md).

---

## Discovery

### `tables()`
No arguments. Returns a list of the searchable table names.

### `columns(*, return_data_as='', output_file='', sort_by='', **filters)`
Structured metadata about searchable columns. Returns a DataFrame (default), `list`, or TSV. Each row:
`table`, `column`, `data_type`, `nullable`, `description`. Filter arguments (all accept wildcards `*`,
case-insensitive):
- `table=` / `exclude_table=` — restrict (or exclude) by table name.
- `column=` — restrict by column name, e.g. `columns(column=['*project*'])`.
- `data_type=` — by type (`text`, `integer`, `bigint`, `boolean`).
- `nullable=` (bool) — only nullable / only required columns.
- `description=` — substring match on the prose description (wildcards auto-applied), e.g.
  `columns(description='age')`.
- `sort_by=` — e.g. `['table', 'nullable:desc', 'column:asc']`.

### `column_values(column, *, return_data_as='dataframe', output_file='', sort_by='', filters='', data_source='', force=False)`
Distinct values in `column` with an occurrence count each. **Run this before filtering** to learn the
real spelling/casing of values.
- `column` (**required**) — the column name.
- `filters=` — keep only values matching these strings (wildcards; `''` matches/counts NULLs).
- `data_source=` — restrict to one source (`'GDC'`, …). *Only one source per call.*
- `sort_by=` — `'count'` (default for dataframe/tsv) or `'value'` (default for list); `:asc`/`:desc`.
- `force=True` — required to run on huge ID-like columns (otherwise you get a warning instead of a
  costly query).
- Counts are **per row in the column's home table** (e.g. `diagnosis` counts observations, not
  subjects), so they can exceed the subject count.
- `return_data_as` accepts only `'dataframe'` (default; columns `['<col>', 'value_count']`), `'list'`
  (bare values), or `'tsv'` — **not `'dict'`** (that's a `summarize_*`-only option and errors here).

---

## Summaries — size & profile a result set first

### `summarize_subjects(...)` / `summarize_files(...)`
Same search arguments as above, plus:
- **`return_data_as=`** — `'dataframe_list'` (list of DataFrames), `'dict'`, or `'json'` (with
  `output_file=`). **If omitted, the summary tables are pretty-printed to stdout and nothing is
  returned** — pass `return_data_as='dict'` when you need the values in code.

Returns, per summarized column, a count of each value (or min/quartiles/mean/max for unbounded numerics
like `year_of_birth`). Two special keys/frames always appear:
- `summarize_subjects` → `number_of_matching_subjects`, `number_of_files_related_to_matching_subjects`.
- `summarize_files` → `number_of_matching_files`, `number_of_subjects_related_to_matching_files`.

The summary also profiles `data_source` — the **cross-repository Venn** of the result set (how many
subjects are GDC-only vs GDC+IDC vs PDC+GDC+IDC, …). See [CROSS-REPOSITORY.md](CROSS-REPOSITORY.md).

> Count files with `summarize_files` and subjects with `summarize_subjects`. The "related files" count
> on a subject summary has historically been unreliable — for an authoritative file count, query files.

---

## Fetch rows

### `get_subject_data(...)` / `get_file_data(...)`
Same search arguments, plus:
- **`collate_results=`** (bool) — if `True`, related data from joined (`add_columns`) tables is bundled
  per result row into a nested, **row-aligned** DataFrame column named `<table>_data` (e.g. `file_data`,
  `observation_data`) — verified `(297, 12)` for the subject above, with `file_id`/`format`/`drs_uri`
  correctly aligned. This is the **only** way to get trustworthy per-item rows; the default list-packing
  (above) is not alignable. Explode the nested frame with `expand_*_results()`.
- **`include_external_refs=`** (bool, **subjects only**) — attach an **`external_reference_data` column
  whose cells are per-subject DataFrames** (`type, name, short_name, last_updated, uri, description,
  source_short_name, source_url`) of links to external resources. Populated only for subjects with
  ISB-CGC/GDC-derived resources (e.g. TCGA, CPTAC); the cell is an **empty** DataFrame for subjects
  without them (e.g. ICDC) — so test it on a TCGA subject, not a canine one.
- **`return_data_as=`** — `'dataframe'` (default) or `'tsv'` (with `output_file=`).

Returns one row per subject / per file. `get_file_data` rows include `drs_uri` (the cloud handle) and
`access` (`open`/`controlled`). For large pulls, write straight to TSV:
`get_subject_data(match_all='project_name = *cptac*', return_data_as='tsv', output_file='cptac.tsv')`.

---

## Combine & reshape results

### `intersect_subject_results(*dfs, ignore_added_columns=False)` / `intersect_file_results(...)`
Merge two or more result DataFrames by **intersection** — keep only entities present in **all** inputs,
combining their data. This is how you express "subjects matching A **AND** B" when A and B can't be one
filter (e.g. has a *tumor* BAM AND has a *normal* BAM — same column, two values). Set
`ignore_added_columns=True` to merge only the base subject/file columns when added columns from
different upstream queries won't reconcile.

```python
normal = get_subject_data(match_all=['tumor_vs_normal = normal', 'format = bam'])
tumor  = get_subject_data(match_all=['tumor_vs_normal = tumor',  'format = bam'])
both   = intersect_subject_results(normal, tumor)   # subjects with both
```

> **`intersect_subject_results` is reliable; `intersect_file_results` can break.** In 2.1.0, file
> intersection raises *"Unexpectedly encountered different clashing values … column 'data_source':
> ['GDC'] vs ['GDC','GDC','GDC',…]. Cannot continue"* when the two inputs collated the base
> `data_source` list column differently — and `ignore_added_columns=True` does **not** help (it's a base
> column, not an added one). Fall back to intersecting on the id directly:
> ```python
> shared = set(a['file_id']) & set(b['file_id'])
> both   = a[a['file_id'].isin(shared)]
> ```
> When you need an AND across two *file* conditions, it's often cleaner to express the cohort at the
> subject level (`intersect_subject_results`) and then pull files.

### `expand_subject_results(df, '<column>_data')` / `expand_file_results(...)`
Explode a collated nested column (produced by `collate_results=True`) into **one row per item**, so
each row's values line up (which `file_id` is the CT vs the mutation file). Confirm the exact file-side
function name with `cda_functions()`.

```python
ct  = get_subject_data(match_all=['anatomic_site = *kidney', 'file_type = CT Image Storage'],
                       add_columns='file.*', collate_results=True)
mut = get_subject_data(match_all=['anatomic_site = *kidney', 'file_type = Annotated Somatic Mutation'],
                       add_columns='file.*', collate_results=True)
expand_subject_results(intersect_subject_results(ct, mut), 'file_data')
```

---

## Release metadata

### `release_metadata(*, return_data_as='dataframe', output_file='', sort_by='', debug=False, **filters)`
The authoritative freshness/provenance source — returns one record per (table, column, source) with the
upstream version and row counts. Default returns a list of dicts (≈151 in the March 2026 release); each:
`cda_table`, `cda_column`, `data_source`, `data_source_version`, `data_source_extraction_date`,
`data_source_row_count`, `data_source_unique_value_count`, `data_source_null_count`. `data_source` is
`CDA` (the harmonized aggregate) plus the five upstreams (`GDC`, `PDC`, `IDC`, `GC`, `ICDC`). Cite this
rather than guessing how current CDA is. Equivalent REST endpoint: `GET /release_metadata/`.

```python
release_metadata()[0]
# {'cda_table':'file','cda_column':'access','data_source':'CDA','data_source_version':'March 2026',
#  'data_source_extraction_date':'2026-03-25','data_source_row_count':3426124, ...}
```

---

## Configuration

### `set_api_url(url)` / `get_api_url()`
`get_api_url()` returns the active endpoint; in cdapython 2.1.0 it already defaults to production
`https://cda.datacommons.cancer.gov`, so `set_api_url()` is **optional** (call it only to pin/change the
host — e.g. a `cda-dev.datacommons.cancer.gov` test host). The trailing slash does not matter.

### `cda_functions()`
Lists the functions available in your installed version — the authoritative source if a name here has
drifted across releases. The names it returns are the **entire** user-facing surface; other entries in
`dir(cdapython)` (`get_data`, `summarize`, `discover`, `validation`, `application_utilities`,
`logging_wrappers`) are **internal modules, not callable APIs**.

### Logging
`set_log_level(...)`, `get_log_level()`, `get_valid_log_levels()`, `enable_console_logging()` /
`disable_console_logging()`, `enable_file_logging()` / `disable_file_logging()` control cdapython's
diagnostics — useful when a query errors (e.g. to see the "not a searchable CDA column" message in full).
