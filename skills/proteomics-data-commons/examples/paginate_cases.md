# Paginate a full result set

PDC's `getPaginated*` and `*PerStudy` queries require `offset` and `limit`. They return a `pagination`
block too — **but treat `pagination` as unreliable: under load PDC routinely returns the list
populated with `pagination: null`** (verified on `getPaginatedCases`). So drive the loop off the
**page length** (stop on a short page), not off `pagination.total`, and retry the transient null
payloads. See [../references/PAGINATION.md](../references/PAGINATION.md).

## Example: all cases (robust loop)

```python
import time, requests
URL = "https://proteomic.datacommons.cancer.gov/graphql"

def pdc(query, tries=5):
    """POST with retry on PDC's transient null-data responses (HTTP 200, no `errors`, data null)."""
    for k in range(tries):
        body = requests.post(URL, json={"query": query}, timeout=180).json()
        if body.get("errors"):
            raise RuntimeError(body["errors"])
        data = body.get("data")
        if data and all(v is not None for v in data.values()):
            return data
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

def all_cases(page=1000):
    out, offset = [], 0
    while True:
        d = pdc('{ getPaginatedCases(offset: %d limit: %d) '
                '{ cases { case_submitter_id project_submitter_id disease_type } } }' % (offset, page))
        cases = d["getPaginatedCases"]["cases"]
        out.extend(cases)
        offset += page
        if len(cases) < page:          # short page => done (no dependence on pagination.total)
            return out

cases = all_cases()
print(len(cases), "cases")             # 6190

from collections import Counter
for disease, n in Counter(c["disease_type"] for c in cases).most_common(10):
    print(f"{n:5}  {disease}")
```

## Generic loop for any paginated query

```python
def paginate(make_query, query_field, list_key, page=1000):
    """make_query(offset, limit) -> GraphQL string selecting `query_field { ... list_key [...] }`."""
    out, offset = [], 0
    while True:
        payload = pdc(make_query(offset, page))[query_field]
        rows = payload[list_key]
        out.extend(rows)
        offset += page
        if len(rows) < page:
            return out

# e.g. every file in a study (getPaginatedFiles needs study_id):
# files = paginate(
#     lambda o, l: '{ getPaginatedFiles(study_id:"%s" offset:%d limit:%d) { files { file_id file_name file_type } } }' % (STUDY_ID, o, l),
#     query_field="getPaginatedFiles", list_key="files")
```

## Notes

- **`pagination` is unreliable; page length is not.** A page shorter than `limit` is the last page —
  the one signal that's always present. If you *do* read `pagination.total`, guard against it being
  null and retry the call.
- **Both args are required.** Omitting `offset`/`limit` errors or returns a tiny default page.
- **`limit` ≤ 25000.** Use modest pages (500–2000) for the `*PerStudy` queries flagged "huge volume of
  data"; large pages can be slow and make the transient-null retries more frequent.
- `allCases` and `getPaginatedGenes` bake `offset`/`limit` into their query text; prefer the
  `getPaginated*` variants with this loop for full retrieval.
