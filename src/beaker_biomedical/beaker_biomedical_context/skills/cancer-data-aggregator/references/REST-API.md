# REST service

`cdapython` is the supported, fuller-featured interface; the REST service is the lower-level layer it
calls. Use REST directly only when Python is unavailable, or for the simplest exact-match / linkage /
catalogue queries. **Mind the semantic differences below** — REST is not a 1:1 stand-in for the client.

- **Base URL:** `https://cda.datacommons.cancer.gov/` (production, verified live). No auth, ever.
- **OpenAPI spec (verbatim):** [../assets/service_openapi.yaml](../assets/service_openapi.yaml).
- HTTP 200 on success; **400** → `ClientError {error_type, message}`; **422** → validation error;
  **500** → `InternalError`.

## Endpoints (7)

| Method & path | Body | Returns |
|---|---|---|
| `POST /data/subject?limit&offset` | `DataRequestBody` | `PagedResponseObj` — subject rows |
| `POST /data/file?limit&offset` | `DataRequestBody` | `PagedResponseObj` — file rows |
| `POST /summary/subject` | `SummaryRequestBody` | `SummaryResponseObj` — subject value-counts |
| `POST /summary/file` | `SummaryRequestBody` | `SummaryResponseObj` — file value-counts |
| `POST /column_values/{column}?data_source&limit&offset` | (none) | `ColumnValuesResponseObj` |
| `GET /columns/` | — | `ColumnResponseObj` — the 105-column catalogue |
| `GET /release_metadata/` | — | per table/column/source row counts, versions, extraction dates |

`limit` defaults to **100**, `offset` to **0** on the `/data/*` endpoints.

## Request bodies (note the UPPER_CASE keys)

`DataRequestBody` (and `SummaryRequestBody`, which omits the last two):

```jsonc
{
  "SEARCH_LIST":     ["kidney"],                  // positional global keyword terms (AND'd)
  "MATCH_ALL":       ["species = human"],         // filter strings, all must hold
  "MATCH_SOME":      ["anatomic_site = kidney"],  // filter strings, at least one (== match_any)
  "ADD_COLUMNS":     ["observation.*"],           // join other tables — the `.*` is REQUIRED
                                                  //   (bare "observation"/"mutation" -> 400 ColumnNotFound)
  "EXCLUDE_COLUMNS": [],
  "COLLATE_RESULTS":   false,                     // DataRequestBody only
  "EXTERNAL_REFERENCE": false                     // DataRequestBody only (subjects)
}
```

All fields are optional and default to empty. There is no `data_source` field in the body — restrict by
source with the boolean columns in `MATCH_ALL` (`subject_data_at_gdc = true`; AND two of them for the
overlap) or, for `column_values`, the `?data_source=` query parameter. **These `<table>_data_at_<dc>`
booleans (and `<table>_data_source_count`) are a REST capability** — `cdapython` cannot filter on them
and uses its `data_source=` argument instead (see [FILTERS.md](FILTERS.md),
[CROSS-REPOSITORY.md](CROSS-REPOSITORY.md)). A `subject_*` boolean is valid in a `file` query (e.g. BAM
files whose subject also has PDC data → 23,044), but `file_data_at_pdc` is ~0 since files are
single-homed.

## Response shapes

`PagedResponseObj` / `ColumnValuesResponseObj`:

```jsonc
{
  "result": [ { "...": "..." } ],   // list of row objects
  "query_sql": "SELECT ...",        // the SQL CDA generated (handy for debugging)
  "total_row_count": 12345,         // total matches, ignoring paging
  "next_url": "https://.../data/subject?limit=100&offset=100"  // null on the last page
}
```

`SummaryResponseObj` has `result` + `query_sql` (no paging). Its single result object holds
`total_count`; a cross-entity count that **differs by endpoint** — `file_count` on `/summary/subject`
but **`subject_count` on `/summary/file`** (not `file_count`); a `data_source` Venn dict (31
exclusive-combination keys); and one `<column>_summary` per profiled column, each a list of `{<column>:
value, count_result: N}`. **Exception:** the `*_data_source_count_summary` entries are a single numeric
stats object `{min, max, mean, median, lower_quartile, upper_quartile}`, not a value-count list — don't
iterate them as `{value, count_result}`. (cdapython's `summarize_*(return_data_as='dict')` uses
different key names: `number_of_matching_subjects`/`number_of_files_related_to_matching_subjects` and
bare column names, not `*_summary`.)
`ReleaseMetadataObj` / `ColumnResponseObj` carry just `result`.

## Pagination

`/data/*` **and** `/column_values/{column}` page with `limit` + `offset` (both return `total_row_count`
+ `next_url`); loop until `next_url` is null (or `offset ≥ total_row_count`). Note `next_url` may come
back with an **`http://`** scheme — upgrade it to `https://` if your client enforces TLS.

```python
import requests
B = "https://cda.datacommons.cancer.gov"
def fetch_all(entity, body, limit=1000):
    rows, offset = [], 0
    while True:
        r = requests.post(f"{B}/data/{entity}?limit={limit}&offset={offset}", json=body, timeout=120)
        r.raise_for_status()
        d = r.json()
        rows += [x for x in d["result"] if x]
        if not d.get("next_url") or len(d["result"]) < limit:
            return rows, d.get("total_row_count")
        offset += limit
```

## REST ≠ cdapython — the differences that bite

- **No `*` wildcards.** `MATCH_ALL` matches values **exactly** (case-insensitive); `*` and SQL `%` are
  taken literally and match nothing. Verified: `"diagnosis = *adenocarcinoma*"` → `total_row_count 0`,
  `"diagnosis = %Adenocarcinoma%"` → 0, but `"diagnosis = Adenocarcinoma"` → 11,794 (and `"... =
  adenocarcinoma"` also 11,794 — case-insensitive). For partial matches, use `cdapython`, or enumerate
  exact values with `/column_values/{column}` and OR them into `MATCH_SOME`.
- **No client-side reshaping.** `intersect_*`, `expand_*`, the TSV/DataFrame conveniences, and
  `match_from_file` are client features — do that work yourself over the JSON.
- **Filter strings still need spaces around the operator** (`"age_at_observation > 50"`).
- **`column_values` counts are per-row in the home table** (e.g. observations for `diagnosis`), so they
  can exceed the subject `total_count` for the same value.

## Quick examples

```python
import requests
B = "https://cda.datacommons.cancer.gov"

# Distinct values of a column (no body needed)
requests.post(f"{B}/column_values/sex").json()["result"]
# -> [{"sex":"female","value_count":82514}, {"sex":"male","value_count":100165}, {"sex":null,...}]

# Cross-repository count: subjects at both GDC and PDC
requests.post(f"{B}/summary/subject",
              json={"MATCH_ALL": ["subject_data_at_gdc = true", "subject_data_at_pdc = true"]}
             ).json()["result"][0]["total_count"]   # -> 2345

# What's in the current release
requests.get(f"{B}/release_metadata/").json()["result"][0]
```

See [../examples/rest_api.md](../examples/rest_api.md).
