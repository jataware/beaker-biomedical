# Troubleshooting & gotchas (verified, cdapython 2.1.0)

The fixes for the failure modes that actually bite, each verified live (CDA March 2026 release). When a
query errors or returns a surprising count, check here before assuming the data is missing.

## "Requested column 'X' is not a searchable CDA column"

You filtered on a column that exists in the REST catalogue but isn't in cdapython's 64 searchable
columns. The usual culprits are the **linkage/key columns**: `<table>_data_at_<dc>`,
`<table>_data_source_count`, `<table>_crdc_id`, `<table>_id_alias`.

- **Cross-repository membership** → use the **`data_source=`** argument, not the booleans:
  `summarize_subjects(data_source=['GDC','PDC'])` (a list ANDs) — *not*
  `match_all=['subject_data_at_gdc = true', ...]` (REST-only).
- Run `columns()` (or `columns(column=['*name*'])`) to confirm a name is searchable before filtering.

## `summarize_*` returned `None` (or `AttributeError: 'NoneType' object has no attribute 'get'`)

By default `summarize_subjects`/`summarize_files` **pretty-print to stdout and return nothing**. To get
values in code, pass `return_data_as='dict'` (or `'dataframe_list'` / `'json'`):

```python
d = summarize_subjects(match_all=['species = human'], return_data_as='dict')
d['number_of_matching_subjects']
```

## A `*wildcard*` filter returns 0

`*` partial matching is a **cdapython client feature**. It works in `cdapython`
(`'diagnosis = *adenocarcinoma*'` → 15,547) but is taken literally by the **REST** API (→ 0). Over REST,
enumerate exact values with `column_values` and OR them into `MATCH_SOME`. See
[REST-API.md](REST-API.md).

## A filter raises a parse error / matches nothing unexpectedly

Filter strings need **spaces around the operator**: `'age_at_observation > 50'`, never
`'age_at_observation>50'`. `< <= > >=` are numeric-only; `=`/`!=` work on text (case-insensitive). Use
`NULL` for missing data (`'cause_of_death = NULL'`). At REST these are **4xx with a typed body**, never a
silent empty `200`: a missing column → `400 {"error_type":"ColumnNotFound"}`, a spaceless operator →
`400 {"error_type":"ParsingError"}`. Check the status code.

## `column_values` returned a warning instead of data (gene/ID columns)

High-cardinality columns — `hugo_symbol`, `entrez_gene_id`, and the `*_id`/`*_barcode`/`*_uuid` columns
— are **blocked by default** ("very large number of values; retrieval is blocked"). Pass
**`force=True`**. A `filters=` restriction alone does **not** lift the block:
`column_values('hugo_symbol', filters='TP53', force=True)` → `['TP53']`.

## `columns(description=...)` returned columns that have nothing to do with my term

`description=` is a **substring match over the prose description**, so it's noisy —
`columns(description='age')` also returns `file_type` ("CT im**age**"), `year_of_*`, and `subject_id`.
Treat it as a *narrowing* tool: read the matched descriptions and pick the right column; don't assume a
single hit.

## `intersect_file_results` raised "clashing values … column 'data_source'"

A 2.1.0 bug: file intersection chokes when the two inputs collated the base `data_source` list column
differently (`['GDC']` vs `['GDC','GDC',…]`), and `ignore_added_columns=True` does **not** help (it's a
base column). Intersect on the id instead — `set(a['file_id']) & set(b['file_id'])` — or express the AND
at the **subject** level (`intersect_subject_results` is reliable) and then pull files.

## My `!=` filter returned the same rows as `=` (excluded nothing)

**`!=` is broken on string/controlled-term columns** — the service compiles it to the same SQL as `=`.
Verified: `race != White` → 33,613 = `race = White`; same for `sex`, `vital_status`, `diagnosis`,
`format`, … It works only on numeric columns. To exclude a string value, enumerate the alternatives with
`match_any`, or use `'col = NULL'` logic. (`'col != NULL'` is fine — separate code path.)

## My cohort is far smaller than expected (mostly-NULL column)

Most clinical columns are mostly null, so an equality filter silently drops the missing majority:
`age_at_observation` 97.5% null, `treatment_anatomic_site` ~100%, `grade` 95%, `stage` 93%,
`vital_status` 88%, `diagnosis` 69%. Profile with `'col = NULL'` first. Also: `age_at_observation` tops
out at **90** (90+ are HIPAA-masked to 90) and there's no age summary in `summarize_*` output.

## Wildcard / search errored or returned nothing

`*` is allowed only at the **ends** of a value — a middle `*` (`'diagnosis = Endo*carcinoma'`) is a hard
error. A positional `search_terms` arg with a **space is a literal phrase** (`'lung adenocarcinoma'`
errors with "yielded no results"); AND separate words as separate args (`'lung', 'adenocarcinoma'`).

## `column_values(col, data_source='IDC')` hung or raised `JSONDecodeError: Expecting value`

That's a server **read-timeout (>300 s)** on a high-cardinality IDC column (`anatomic_site`,
`tumor_vs_normal`), mis-surfaced as a JSON error. Use `summarize_files(data_source='IDC')[...]` or filter
the cohort first.

## A value filter under-counts

Stored casing varies by column (`sex` lowercase, `format` UPPERCASE, `diagnosis` title-case). Exact
matching is case-insensitive, but a *partial* match needs the right stem. Always
`column_values('col')` first. `column_values` counts are **per row in the column's home table** (e.g.
`diagnosis` counts observations, not subjects), so they can exceed the subject total — that's expected.

## `file_data_source_count > 1` / `data_source=[list]` on files returns 0

**Files are single-homed** — each file physically lives in exactly one repository. Cross-repository
overlap is a **subject** concept. Find the overlapping *subjects* first
(`data_source=['GDC','PDC']`), then pull their files.

## Wrong/empty count off a subject query's "related files"

Count files with **`summarize_files`/`get_file_data`** and subjects with the subject functions. The
"related files" number on a subject summary has historically been unreliable.

## My `add_columns` lists don't line up / zipping gives wrong pairs

`add_columns` does **not** fan rows out — it packs each added column into a **list cell** per result
row, and those lists are **independently de-duplicated, so different columns have different lengths**
(verified: 297 `file_id`s but 16 `format`s for one subject). The same hits `upstream_identifiers.*`
(source vs id lists differ) and `mutation.*`. **Never zip these columns.** Pass `collate_results=True`
to get a nested, row-aligned `<table>_data` frame, then `expand_subject_results(df, '<table>_data')`
(e.g. `'file_data'`, `'observation_data'`, `'upstream_identifiers_data'`). See
[../examples/intersect_cohorts.md](../examples/intersect_cohorts.md).

## `add_columns='observation.diagnosis'` errored

You can only add a **whole table** (`'observation.*'`) or a **bare** column name (`'diagnosis'`). A
table-qualified single column (`'observation.diagnosis'`) is rejected as "neither a column nor a
`table.*` macro."

## Which interface am I really on?

- **cdapython 2.1.0**: 64 searchable columns; `data_source=` for repos; `*` wildcards; result rows carry
  a `data_source` list column; summary venn uses human keys (`'PDC and GDC'`).
- **REST**: 105-column catalogue; `data_at_*` booleans filterable in `MATCH_ALL`; exact-match only (no
  `*`); summary venn uses `*_exclusive` keys (`gdc_pdc_exclusive`). No `data_source` body field.

## Citing freshness

Cite `release_metadata()` (cdapython) or `GET /release_metadata/` — don't guess. Current aggregate at
time of writing: **March 2026** release, extracted 2026-03-25.
