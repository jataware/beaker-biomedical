# Quickstart: calling CDA

CDA has two interfaces. Prefer **`cdapython`** (richer: `*` wildcards, `intersect_*`/`expand_*`, TSV/
DataFrame output, `match_from_file`). The **REST** service is a lightweight fallback when Python isn't
available — see [rest_api.md](rest_api.md). Neither needs authentication.

## cdapython (preferred)

```bash
pip install git+https://github.com/CancerDataAggregator/cdapython.git@develop   # Python 3.9+
```

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")   # production; trailing slash matters

cda_functions()    # list available functions for your installed version
tables()           # subject, file, observation, project, treatment, mutation, upstream_identifiers
```

A first query — size a cohort before pulling rows (prints summary tables to stdout):

```python
summarize_subjects('kidney')                         # global keyword search, all columns
summarize_subjects(match_all=['species = human', 'sex = female'])
```

Then fetch the rows you want (one row per subject; write big pulls straight to TSV):

```python
df = get_subject_data(match_all=['diagnosis = *adenocarcinoma*', 'species = human'])
get_subject_data(match_all='project_name = *cptac*',
                 return_data_as='tsv', output_file='cptac_subjects.tsv')
```

## REST (fallback, no install beyond `requests`)

```python
import requests
B = "https://cda.datacommons.cancer.gov"

# What's in the current release (no body, no auth)
print(requests.get(f"{B}/release_metadata/").json()["result"][0])

# A summary count
r = requests.post(f"{B}/summary/subject", json={"MATCH_ALL": ["species = human", "sex = female"]})
print(r.json()["result"][0]["total_count"])
```

## Two things to remember

- **Prefer `cdapython` for anything with a partial match.** The `*` wildcard
  (`'diagnosis = *adenocarcinoma*'`) is a client feature; raw REST matches values **exactly** and would
  return 0 for that string. See [../references/REST-API.md](../references/REST-API.md).
- **Check values before filtering.** `column_values('col')` shows the real spelling/casing — `sex` is
  lowercase, `format` is uppercase, `diagnosis` is title-case. Filter-string operators need spaces:
  `'age_at_observation > 50'`, not `'age_at_observation>50'`.

## CDA locates; it does not download or analyze

`get_file_data` rows carry a `drs_uri` and an `access` flag — that's the handoff point. To fetch bytes,
resolve the DRS URIs in a cloud workspace ([files_and_drs.md](files_and_drs.md)); for gene-expression /
mutation-frequency / survival analysis, hand the located data to `genomic-data-commons` (or the
relevant commons' skill). See [../references/CROSS-REPOSITORY.md](../references/CROSS-REPOSITORY.md).
