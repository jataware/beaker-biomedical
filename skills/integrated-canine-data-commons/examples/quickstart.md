# Quickstart: calling the ICDC GraphQL API

ICDC is a single GraphQL endpoint with **no authentication** and **POST only**. This is the request
helper the other examples build on.

## The helper

```python
import requests

URL = "https://caninecommons.cancer.gov/v1/graphql/"   # trailing slash; POST only

def icdc(query, variables=None, tries=3):
    """POST a GraphQL query to ICDC and return the `data` block. Raises on GraphQL errors."""
    for _ in range(tries):
        r = requests.post(URL, json={"query": query, "variables": variables or {}}, timeout=120)
        r.raise_for_status()                       # transport-level HTTP errors
        body = r.json()
        if body.get("errors"):                     # ICDC returns HTTP 200 even on query errors!
            raise RuntimeError(body["errors"])
        if body.get("data") is not None:
            return body["data"]
    raise RuntimeError("ICDC returned null data after retries")

print(icdc("{ numberOfPrograms numberOfStudies numberOfCases numberOfSamples "
           "numberOfFiles volumeOfData schemaVersion }"))
# {'numberOfPrograms': 5, 'numberOfStudies': 18, 'numberOfCases': 1029, 'numberOfSamples': 1613,
#  'numberOfFiles': 3010, 'volumeOfData': 41850796774931.0, 'schemaVersion': '2.0.0'}
```

`volumeOfData` is bytes (≈ 41.9 TB here). `numberOfAliquots` is always 0 — ICDC has no aliquot layer.

## POST only

A **GET is rejected** — there is no GET path on this endpoint:

```python
requests.get(URL).json()
# {'errors': [{'message': 'API will only accept POST requests'}], 'data': None}
```

## Error handling

ICDC answers query errors with **HTTP 200** and an `errors` array — `raise_for_status()` alone won't
catch them; always inspect `errors` (the helper does). Common messages:

- `Validation error (FieldUndefined@...) : Field 'foo' ... is undefined` — you invented a field or
  asked for a field on the wrong type (e.g. `acl` is on `FileDetail`, not the raw `file` node). Check
  [../references/QUERIES.md](../references/QUERIES.md) / [../references/ENTITIES.md](../references/ENTITIES.md),
  or introspect: `{ __type(name:"case"){ fields { name } } }`.
- An **empty list with no error** usually means a filter *value* didn't match the controlled
  vocabulary (wrong spelling/case), **not** that the data is absent. Discover valid values from
  `searchCases` facet counts first — see [faceted_search.md](faceted_search.md).

## Three things to remember

- **POST only; inspect `errors` (HTTP 200 on failure).**
- **Page size varies by query family.** Portal `*Overview`/`globalSearch` default to `first: 10`;
  node queries (`case`, `file`, …) return *everything* unless you set `first`. See
  [../references/PAGINATION.md](../references/PAGINATION.md).
- **No auth, ever, and no controlled tier.** All metadata, search, and files are open
  ([../auth.yaml](../auth.yaml)); the API doesn't stream bytes — see
  [files_and_download.md](files_and_download.md).
