# Count cases by primary site within a program

`facets=` paired with `size=0` returns aggregate counts without paying the cost of fetching the
underlying records. The pattern: a `filters` clause scopes the cohort, `facets` names the field to
bucket by, and the response carries `data.aggregations.<field>.buckets[]`.

Below: count TCGA cases broken down by `primary_site`.

## Example

```python
import requests, json

filters = {
    "op": "in",
    "content": {"field": "project.program.name", "value": ["TCGA"]},
}

params = {
    "filters": json.dumps(filters),
    "facets": "primary_site",
    "size": 0,
}

r = requests.get("https://api.gdc.cancer.gov/cases", params=params)
r.raise_for_status()
data = r.json()

# Invalid facet names return 200 with a warning, not a 400. Check first.
if "facets" in data.get("warnings", {}):
    raise RuntimeError(f"GDC rejected the facet: {data['warnings']['facets']}")

buckets = data["data"]["aggregations"]["primary_site"]["buckets"]
for b in sorted(buckets, key=lambda b: -b["doc_count"]):
    print(f"{b['doc_count']:6d}  {b['key']}")
```

`data.pagination.total` still gives the total case count under the cohort filter; `buckets` only
covers the dimension you asked to facet on.

To break down by a field that lives in a nested array (e.g. `diagnoses.ajcc_pathologic_stage`), use
the dotted path. If you guess wrong — for example `diagnoses.tumor_stage`, which is not a real GDC
field — the response will come back with `warnings.facets: "unrecognized values: [...]"` and no
`aggregations` key. See [../references/FACETS.md](../references/FACETS.md) for the curated list of
valid facet field names per endpoint.
