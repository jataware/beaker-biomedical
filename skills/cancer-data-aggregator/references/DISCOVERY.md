# Discovery: finding the right table, column, and value

You can't filter well on a column you haven't confirmed exists, or a value you've guessed the spelling
of. CDA gives you a three-step discovery loop — always run it before composing a real query.

## 1. `tables()` — the 7 searchable tables

```python
tables()   # subject, file, observation, project, treatment, mutation, upstream_identifiers
```

`subject` and `file` are the entities you query; the rest are joined via `add_columns='<table>.*'`. See
[DATA-MODEL.md](DATA-MODEL.md).

## 2. `columns(...)` — find the column (don't guess)

`columns()` exposes **64 searchable columns** in cdapython (the REST `/columns/` catalogue lists 105,
the extra 41 being REST-only linkage/key columns — see [DATA-MODEL.md](DATA-MODEL.md)). Search them by
name, table, or description rather than inventing one:

```python
columns(column=['*project*'])      # columns whose name contains "project"
columns(table='file')              # everything on the file table
columns(description='age')         # columns whose description mentions age -> age_at_observation
columns(table='observation', data_type='text')
```

Each row gives `table`, `column`, `data_type`, `nullable`, `description`. A typical discovery: "I want
patient age" → `columns(description='age')` → pick `age_at_observation` (on `observation`, in years).

> **`description=` is a substring match — expect noise, scan the results.** `columns(description='age')`
> also returns `file_type` (its description says "CT **im­age**"), `year_of_observation`, `year_of_birth`,
> `year_of_death`, and `subject_id`. It narrows the field; it does not hand you one answer. Read the
> matched `description`s and choose.

## 3. `column_values('col')` — see the real values & their casing

Before filtering on a value, confirm it exists and how it's spelled/cased (matching is case-insensitive
for exact values, but partial matching needs the right stem):

```python
column_values('format')                       # BAM, BAI, VCF, BCR XML, ... (UPPERCASE)
column_values('anatomic_site', filters='*kidney*')   # all the ways "kidney" appears
column_values('species')                      # human, mouse, dog, human/mouse xenograft, null
column_values('diagnosis', data_source='GDC') # values, restricted to one repository
```

- `filters=` accepts wildcards; `''` matches and counts NULLs.
- Counts are **per row in the column's home table** — `column_values('diagnosis')` counts observations,
  so a value's count can exceed the number of distinct subjects with it.
- **High-cardinality columns are blocked by default** — gene/ID-like columns (`hugo_symbol`,
  `entrez_gene_id`, the `*_id`/`*_barcode`/`*_uuid` columns) return a *warning instead of data*. Pass
  **`force=True`** to run them. **A `filters=` restriction does NOT bypass the block** — verified:
  `column_values('hugo_symbol', filters='TP53')` is blocked, `column_values('hugo_symbol',
  filters='TP53', force=True)` → `['TP53']`.
- `column_values` accepts **one** `data_source` per call.

## Worked discovery → query

```python
# "Adenocarcinoma patients over 60" — discover, then filter.
columns(description='age')                              # several hits; pick age_at_observation (years, observation)
column_values('diagnosis', filters='*denocarcinoma*')  # -> "Adenocarcinoma", "Endometrioid adenocarcinoma", ...
summarize_subjects(match_all=['diagnosis = *adenocarcinoma*',  # * = client partial match
                              'age_at_observation > 60', 'species = human'])
```

Full version: [../examples/find_cohort.md](../examples/find_cohort.md).

## Release & freshness: `release_metadata`

To report what data (and which upstream versions) a result reflects:

```python
import requests
meta = requests.get("https://cda.datacommons.cancer.gov/release_metadata/").json()["result"]
# Each entry: cda_table, cda_column, data_source, data_source_version,
#             data_source_extraction_date, data_source_row_count, ...
```

`release_metadata()` returns **151 records** (one per table/column/source). Sources reported: `CDA` (the
harmonized aggregate) plus the five upstreams — `GDC`, `PDC`, `IDC`, `GC`, `ICDC` (no `CDS` anymore) —
each with its own `data_source_version` and extraction date. Current (March 2026 release, verified live):

| source | data_source_version | extraction |
|---|---|---|
| CDA | `March 2026` | 2026-03-25 |
| GDC | `Data Release 45.0 - December 04, 2025` | 2026-03-02 |
| PDC | `Data Release 5.3` | 2026-03-02 |
| IDC | `v23` | 2025-11-26 |
| GC | `23.0` | 2026-02-17 |
| ICDC | `2025-09-01` | 2026-03-03 |

This is the authoritative "how current is CDA?" answer; cite it rather than guessing.
