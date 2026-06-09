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

There are 105 columns. Search them by name, table, or description rather than inventing one:

```python
columns(column=['*project*'])      # columns whose name contains "project"
columns(table='file')              # everything on the file table
columns(description='age')         # columns whose description mentions age -> age_at_observation
columns(table='observation', data_type='text')
```

Each row gives `table`, `column`, `data_type`, `nullable`, `description`. A typical discovery: "I want
patient age" → `columns(description='age')` → `age_at_observation` (on `observation`, in years).

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
- ID-like columns are flagged as high-overhead; pass `force=True` to run them anyway.
- `column_values` accepts **one** `data_source` per call.

## Worked discovery → query

```python
# "Adenocarcinoma patients over 60" — discover, then filter.
columns(description='age')                              # -> age_at_observation (years, observation)
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

Sources reported: `CDA` (the harmonized aggregate) plus the five upstreams — `GDC`, `PDC`, `IDC`, `GC`,
`ICDC` — each with its own version (e.g. GDC "Data Release 45.0", PDC "5.3", IDC "v23", GC "23.0") and
extraction date. This is the authoritative "how current is CDA?" answer; cite it rather than guessing.
