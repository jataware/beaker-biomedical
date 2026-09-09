# Query patterns: OR, keyword, clinical tables, genes, NULL, canine, errors

A grab-bag of **verified** query shapes beyond the core discover→summarize→fetch loop (run live against
the production service, cdapython 2.1.0 / CDA March 2026 — counts drift with releases). Each shows the
idiom and the real number it returned. Background: [../references/FILTERS.md](../references/FILTERS.md),
[../references/FUNCTIONS.md](../references/FUNCTIONS.md).

```python
from cdapython import *   # already points at production in 2.1.0
```

## OR within a field — `match_any`

`match_any` is OR; combine with `match_all` (which ANDs) and the two AND together:

```python
summarize_files(match_any=['anatomic_site = *kidney*', 'anatomic_site = *bladder*'])
#   number_of_matching_files: 52,536  (kidney OR bladder)

summarize_subjects(match_all=['species = human'], match_any=['sex = male', 'sex = female'])
#   number_of_matching_subjects: 100,949  (human AND (male OR female))
```

## Open-ended keyword search — `search_terms`

Bare positional strings search every column, case-insensitive, AND'd. Good for "what's in here about…":

```python
summarize_subjects('kidney')           # 3,499 subjects tagged kidney anywhere
summarize_subjects('kidney', 'vcf')    # 2,451  (kidney AND vcf)
```

Once you know the column, switch to explicit filters for precision.

## Clinical tables — `treatment`, and the `mutation`/gene caveat

Therapy fields live on `treatment` (join with `add_columns='treatment.*'`):

```python
column_values('treatment_type', return_data_as='list')[:5]
#   ['Ablation or Embolization, NOS', 'Ablation, Cryo', 'Ablation, Ethanol Injection', ...]
column_values('therapeutic_agent', filters='*cisplatin*', return_data_as='list')   # ['Cisplatin']
```

**Gene/ID columns are blocked by default** because they have huge value sets. `column_values` on
`hugo_symbol` (and other ID-like columns) returns a *warning instead of data* — and **a `filters=`
restriction does not bypass the block**; you must pass **`force=True`**:

```python
column_values('hugo_symbol', filters='TP53')              # WARNING: blocked, returns nothing
column_values('hugo_symbol', filters='TP53', force=True)  # ['TP53']
```

> CDA's `mutation` table is GDC-derived with documented unreliable *counts*. For real mutation-frequency
> work, locate the cohort here and hand off to `genomic-data-commons`
> ([handoff_to_gdc.md](handoff_to_gdc.md)).

## Clinical cohorts (exact working strings)

Clinical fields live on `observation`; values are harmonized to CDA's own vocabulary (run
`column_values` first — see [../references/FILTERS.md](../references/FILTERS.md)). Verified counts:

```python
summarize_subjects(match_all=['vital_status = dead'])             # 9,045  (stored lowercase)
summarize_subjects(match_all=['stage = Stage IV'])               #   954
summarize_subjects(match_all=['morphology = Squamous cell carcinoma'])  # 2,702
summarize_subjects(match_all=['race = White', 'ethnicity = Non-Hispanic'])  # GDC-style 'not hispanic...' -> 0
```

## Retrieving mutation data — join only

There is **no `get_mutation_data` and no `/data/mutation`**. Mutation is reachable only by joining
`mutation.*` onto a subject or file query. ⚠️ The joined columns are de-duplicated per subject and **not
row-aligned** — use `collate_results=True` for an aligned per-variant frame, and never trust raw
mutation *counts* (use `genomic-data-commons` for frequency work):

```python
get_subject_data(match_all=['hugo_symbol = TP53'], add_columns='mutation.*', collate_results=True)
#   selects SUBJECTS carrying a TP53 mutation (~5,006) — not mutation occurrences.
```

## Missing data — `NULL`

`NULL` matches absent values; `!= NULL` requires presence. Useful for gauging field coverage:

```python
summarize_subjects(match_all=['cause_of_death = NULL'])    # 180,700  (most subjects lack it)
summarize_subjects(match_all=['cause_of_death != NULL'])   #   1,765  (it's a sparse field)
```

## Non-human / non-GDC data — `data_source`, canine

```python
summarize_subjects(data_source='ICDC')        # 1,029 canine subjects (ICDC = the canine commons)
summarize_subjects(match_all=['species = dog'])# 1,029  (same set — dog data is ICDC)
summarize_subjects(data_source='GC')           # 70,862 subjects with General-Commons data
```

`species` values: `dog`, `human`, `human/mouse xenograft`, `mouse` (+ `<NA>`).

## Compile a program across commons — CPTAC

```python
summarize_subjects(match_all='project_name = *cptac*')   # 3,843 subjects (across GDC+PDC+IDC)
summarize_files(match_all='project_name = *cptac*')      # 270,438 files
```

The `summarize_*` output's `data_source` Venn shows how those split across repositories
([cross_repository.md](cross_repository.md)).

## Match a local list of IDs/values — `match_from_file`

Restrict results to rows whose CDA column matches any value in a column of a local TSV (union/OR
semantics). Verified behavior: missing values are **silently dropped**, matching is **case-insensitive**,
and it works on any column (not just ids):

```python
# my_ids.tsv has a column `subject` of subject_ids (unknown/typo ids are ignored, not an error)
summarize_subjects(match_from_file={'input_file': 'my_ids.tsv', 'input_column': 'subject',
                                    'cda_column_to_match': 'subject_id'})
# Against a value column instead of ids — equivalent to OR-ing the contained values:
#   a file of diagnoses matched to cda_column_to_match='diagnosis' == match_any of those diagnoses.
```

## Raw REST: pagination and error handling

`/data/*` responses carry `total_row_count`, `next_url`, and `query_sql`. Errors are **4xx with a typed
body** — a bad query is never a silent `200` with empty data:

```python
import requests
B = "https://cda.datacommons.cancer.gov"

requests.post(f"{B}/data/subject?limit=5", json={"MATCH_ALL": ["species = human"]}).json()
#   -> {'total_row_count': 103225, 'next_url': '...offset=5', 'query_sql': 'SELECT ...', 'result': [...]}

requests.post(f"{B}/summary/subject", json={"MATCH_ALL": ["notacolumn = x"]}).status_code      # 400
#   body: {"error_type": "ColumnNotFound", "message": "Column Not Found: notacolumn"}
requests.post(f"{B}/summary/subject", json={"MATCH_ALL": ["age_at_observation>50"]}).status_code # 400
#   body: {"error_type": "ParsingError", "message": "Unable to parse out operator ..."}  (need spaces!)
```

See [rest_api.md](rest_api.md) and [../references/TROUBLESHOOTING.md](../references/TROUBLESHOOTING.md).
