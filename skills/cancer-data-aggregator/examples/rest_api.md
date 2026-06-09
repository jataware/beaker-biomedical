# Raw REST usage

Use the REST service when Python/`cdapython` isn't available, or for simple exact-match / linkage /
catalogue queries. It's open (no auth), base `https://cda.datacommons.cancer.gov/`. Full schema:
[../references/REST-API.md](../references/REST-API.md) and the verbatim
[../assets/service_openapi.yaml](../assets/service_openapi.yaml).

```python
import requests
B = "https://cda.datacommons.cancer.gov"
```

## Catalogue & values (GET / no-body POST)

```python
requests.get(f"{B}/columns/").json()["result"]                 # the 105-column catalogue
requests.get(f"{B}/release_metadata/").json()["result"][0]     # release versions + row counts
requests.post(f"{B}/column_values/sex").json()["result"]
# -> [{"sex":"female","value_count":82514},{"sex":"male","value_count":100165},{"sex":null,...}]
requests.post(f"{B}/column_values/format?data_source=GDC").json()["result"]   # restrict to one source
```

## Summaries & cross-repository counts

```python
# subjects with data at BOTH GDC and PDC
body = {"MATCH_ALL": ["subject_data_at_gdc = true", "subject_data_at_pdc = true"]}
r = requests.post(f"{B}/summary/subject", json=body).json()["result"][0]
print(r["total_count"], r["file_count"])          # -> 2345 275617
print(r["data_source"])                           # exclusive cross-DC Venn (…_exclusive keys)
```

Request body keys are UPPER_CASE: `SEARCH_LIST` (global keywords), `MATCH_ALL` (AND filters),
`MATCH_SOME` (OR filters, == `match_any`), `ADD_COLUMNS`, `EXCLUDE_COLUMNS`, and (on `/data/*`)
`COLLATE_RESULTS`, `EXTERNAL_REFERENCE`. All optional.

## Fetch rows + pagination (`limit`/`offset`/`next_url`)

`/data/*` defaults to `limit=100, offset=0`; loop until `next_url` is null:

```python
def fetch_all(entity, body, limit=1000):
    rows, offset = [], 0
    while True:
        d = requests.post(f"{B}/data/{entity}?limit={limit}&offset={offset}",
                          json=body, timeout=120).json()
        rows += [x for x in d["result"] if x]
        if not d.get("next_url") or len(d["result"]) < limit:
            return rows, d.get("total_row_count")
        offset += limit

rows, total = fetch_all("file", {"MATCH_ALL": ["format = BAM", "subject_data_at_pdc = true"]})
```

Each response also returns `query_sql` (the generated SQL — useful for debugging a surprising count).

## The gotcha: REST is exact-match, no `*` wildcards

This is the #1 difference from `cdapython`. Verified live against `/summary/subject`:

```python
def n(match): return requests.post(f"{B}/summary/subject",
                                   json={"MATCH_ALL": match}).json()["result"][0]["total_count"]
n(["diagnosis = *adenocarcinoma*"])   # 0   <- '*' taken literally
n(["diagnosis = %Adenocarcinoma%"])   # 0   <- SQL '%' not supported either
n(["diagnosis = Adenocarcinoma"])     # 11794  <- exact match works...
n(["diagnosis = adenocarcinoma"])     # 11794  <- ...and is case-insensitive
```

So for a partial match over REST, enumerate the exact values first and OR them:

```python
vals = [r["diagnosis"] for r in requests.post(f"{B}/column_values/diagnosis").json()["result"]
        if r["diagnosis"] and "adenocarcinoma" in r["diagnosis"].lower()]
body = {"MATCH_SOME": [f"diagnosis = {v}" for v in vals]}   # OR over every adenocarcinoma variant
requests.post(f"{B}/summary/subject", json=body).json()["result"][0]["total_count"]
```

(In `cdapython` this is just `'diagnosis = *adenocarcinoma*'` — which is why the client is preferred.)

## Notes

- Filter strings still need spaces around the operator (`"age_at_observation > 50"`).
- `column_values` counts are per-row in the column's home table (observations for `diagnosis`), so they
  can exceed a subject `total_count`.
- No `data_source` field in the body — use the `subject_data_at_*` booleans in `MATCH_ALL`, or the
  `?data_source=` query param on `column_values`.
- Errors: HTTP 400 → `{"error_type","message"}`; 422 → validation; 500 → internal. Check the status
  code (unlike some APIs, a bad filter is a 4xx, not a 200 with empty data).
