# Build a clinical cohort: discover → summarize → fetch

Goal: profile adenocarcinoma by age in humans. The reliable path is **discover the column, confirm the
values, size the set, then pull rows** — never guess a column or value. See
[../references/DISCOVERY.md](../references/DISCOVERY.md) and [../references/FILTERS.md](../references/FILTERS.md).

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")
```

## 1. Find the columns

```python
columns(description='age')        # -> age_at_observation (integer, years, on `observation`)
columns(column=['*diagnos*'])     # -> diagnosis (on `observation`)
```

## 2. Confirm the values (and their casing)

```python
column_values('diagnosis', filters='*denocarcinoma*')
# Adenocarcinoma (15603), Endometrioid adenocarcinoma (2358), Papillary adenocarcinoma (1967), ...
# -> stored title-case; a *adenocarcinoma* wildcard catches all the variants.
column_values('species')          # human, mouse, dog, human/mouse xenograft, null
```

Counts here are per **observation** (the column's home table), so they run higher than the distinct
subject count — that's expected.

## 3. Size the cohort with a summary (before pulling rows)

```python
summarize_subjects(match_all=['diagnosis = *adenocarcinoma*', 'age_at_observation != NULL'])
# Profiles the matching subjects: number_of_matching_subjects, plus value-counts for sex, race,
# data_source (the cross-repository Venn), and min/quartiles/mean/max for numeric columns.
```

Refine — drop non-humans, then bucket by age range (chained numeric ranges are allowed):

```python
summarize_subjects(match_all=['diagnosis = *adenocarcinoma*', 'age_at_observation != NULL',
                              'species = human'])
summarize_subjects(match_all=['60 < age_at_observation <= 70', 'diagnosis = *adenocarcinoma*',
                              'species = human'])
```

> If you need the counts in code rather than printed, pass `return_data_as='dict'` (or `'json'` with
> `output_file=`) — by default `summarize_*` pretty-prints and returns nothing.

## 4. Fetch the rows

```python
cohort = get_subject_data(match_all=['60 < age_at_observation <= 70',
                                     'diagnosis = *adenocarcinoma*', 'species = human'])
# one row per subject; columns are the subject table by default.
```

## 5. Bring in related data — and keep it readable

A subject can have many observations, so adding the whole observation table fans rows out. Collate
instead, then read or explode the nested frame:

```python
cohort = get_subject_data(match_all=['60 < age_at_observation <= 70', 'diagnosis = *adenocarcinoma*',
                                     'species = human'],
                          add_columns='observation.*', collate_results=True)
cohort['observation_data'][0]                 # the first subject's observations as a sub-DataFrame
expand_subject_results(cohort, 'observation_data')   # one row per observation, values aligned
```

## Notes

- **Wildcards are a `cdapython` feature.** `'diagnosis = *adenocarcinoma*'` matches every
  adenocarcinoma variant in the client; the same string hits 0 via raw REST (exact-match only) —
  there you'd OR the exact values from `column_values` into `match_any`. See
  [rest_api.md](rest_api.md).
- **Operators need surrounding spaces** and `<,<=,>,>=` are numeric-only; `=`/`!=` work on text and are
  case-insensitive. `NULL` matches missing data.
- **Counts shift between releases** — the numbers above are illustrative; re-run to get current values,
  and cite `release_metadata` for provenance.
- Same pattern for files: swap `summarize_files` / `get_file_data` and file columns (`format`,
  `file_type`, `anatomic_site`, `tumor_vs_normal`). Count files with file queries, subjects with
  subject queries.
