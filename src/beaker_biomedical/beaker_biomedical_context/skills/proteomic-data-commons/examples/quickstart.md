# Quickstart: calling the PDC GraphQL API

PDC is a single GraphQL endpoint with no authentication. This is the request helper every other
example builds on.

## The helper

```python
import time, requests

URL = "https://proteomic.datacommons.cancer.gov/graphql"

def pdc(query, variables=None, tries=5):
    """POST a GraphQL query to PDC and return the `data` block.
    Raises on GraphQL errors; retries the transient null-payload responses PDC emits under load."""
    for k in range(tries):
        r = requests.post(URL, json={"query": query, "variables": variables or {}}, timeout=180)
        r.raise_for_status()                       # transport-level HTTP errors
        body = r.json()
        if body.get("errors"):                     # PDC returns HTTP 200 even on query errors!
            raise RuntimeError(body["errors"])
        data = body.get("data")
        if data:                                   # `data` (or a field of it) can come back null
            return data                            # transiently with no `errors` — see notes below
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

print(pdc("{ getPDCMetrics { programs projects studies cases files data_size_TB } }"))
# {'getPDCMetrics': {'programs': 9, 'projects': 30, 'studies': 227, 'cases': 6239, 'files': 195269, 'data_size_TB': 70}}
```

## GET vs POST

Short queries work as a GET (handy for a quick curl); anything with a deep field set must be POST,
because the encoded query overflows URL length limits.

```python
# GET — requests URL-encodes the query for you
requests.get(URL, params={"query": "{ getPDCMetrics { studies cases } }"}).json()

# curl equivalent
#   curl -s -G 'https://proteomic.datacommons.cancer.gov/graphql' \
#        --data-urlencode 'query={ getPDCMetrics { studies cases } }'
```

```python
# POST — the default for real work
requests.post(URL, json={"query": "{ getPDCMetrics { studies cases } }"}).json()
```

## Error handling

PDC answers query errors with **HTTP 200** and an `errors` array — `raise_for_status()` alone will
not catch them. Always inspect `errors` (the helper above does). Typical messages:

- `Cannot query field "foo" on type "..."` — you invented a field or query name.
- `Matrix data not found! pdc_study_id: PDC000127: <type>` — `quantDataMatrix` with a `data_type` the
  study doesn't have (see [../references/QUANTITATION.md](../references/QUANTITATION.md)).

**Transient null payloads.** Under load, PDC intermittently returns `{"data": null}` — or a populated
top level with a *nested* field null (e.g. `getPaginatedCases.pagination` null while `cases` is fine)
— with **no `errors` array** and HTTP 200. This is transient: the same query succeeds on retry. The
helper above retries on top-level null; when you depend on a nested field, validate it and retry the
call if it's null (see [paginate_cases.md](paginate_cases.md)).

## No auth, ever

There is no API key, token, or header to set — all PDC data is open-access. (See
[../auth.yaml](../auth.yaml).) The only credential-like artifacts are the *signed download URLs* from
`filesPerStudy`, which expire after 7 days — see [study_files_download.md](study_files_download.md).
