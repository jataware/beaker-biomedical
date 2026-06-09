# cdapython function reference

The current `cdapython` (v3+, a full rewrite — older `Q`/`fetch_rows`/`summary_counts` APIs are
retired) exposes a small set of functions. Import everything with `from cdapython import *`. Verbatim
upstream docs: [../assets/cdapython_man_pages.md](../assets/cdapython_man_pages.md).

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")
cda_functions()    # prints the full, authoritative function list for your installed version
```

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
- **`data_source=`** (string or list) — restrict to upstream repositories: `'GDC'`, `'IDC'`, `'PDC'`,
  `'GC'`, `'ICDC'`. Default: no filter.
- **`add_columns=`** — pull columns from another table into the result, e.g. `'observation.*'`,
  `'file.*'`, `'upstream_identifiers.*'`. Can **multiply rows** (join fan-out); pair with
  `collate_results=True`.
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
  per result row into a nested DataFrame column named `<table>_data` (e.g. `file_data`,
  `observation_data`), instead of being flattened/duplicated across rows. Explode it with
  `expand_*_results()`.
- **`include_external_refs=`** (bool, **subjects only**) — attach an `external_reference_data` frame of
  links to external resources for each subject.
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

## Configuration

### `set_api_url(url)`
Point the client at a CDA service. Use production `"https://cda.datacommons.cancer.gov/"` (trailing
slash). The docs' notebooks use a `cda-dev.datacommons.cancer.gov` host for testing.

### `cda_functions()`
Lists the functions available in your installed version — the authoritative source if a name here has
drifted across releases.
