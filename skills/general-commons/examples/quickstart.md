# Quickstart: calling the GC GraphQL API

General Commons is a single GraphQL endpoint with no authentication. This is the request helper the
other examples build on.

> Before going deep in GC, confirm it's the right commons — GC mirrors data from the specialized
> commons. For genomics use `genomic-data-commons`, proteomics `proteomic-data-commons`, imaging the
> imaging-data-commons. See [../references/DISCOVERY.md](../references/DISCOVERY.md).

## The helper

```python
import requests

URL = "https://general.datacommons.cancer.gov/v1/graphql/"   # trailing slash matters

def gc(query, variables=None, tries=3):
    """POST a GraphQL query to GC and return the `data` block. Raises on GraphQL errors."""
    for _ in range(tries):
        r = requests.post(URL, json={"query": query, "variables": variables or {}}, timeout=120)
        r.raise_for_status()                       # transport-level HTTP errors
        body = r.json()
        if body.get("errors"):                     # GC returns HTTP 200 even on query errors!
            raise RuntimeError(body["errors"])
        if body.get("data") is not None:
            return body["data"]
    raise RuntimeError("GC returned null data after retries")

print(gc("{ studiesCount programsCount version { data_version datetime description } }"))
# {'studiesCount': 89, 'programsCount': 9,
#  'version': {'data_version': '12.0.0', 'datetime': '2026-05-06T12:00:10Z', 'description': '2026 May Released GC data'}}
```

## GET vs POST

Short queries work as a GET; anything with a deep field set should be POST so the encoded query doesn't
overflow URL length limits. A GET to the bare endpoint returns the schema.

```python
requests.get(URL, params={"query": "{ studiesCount }"}).json()                 # quick
requests.post(URL, json={"query": "{ studies(first: 5) { phs_accession } }"})  # default for real work
```

## Error handling

GC answers query errors with **HTTP 200** and an `errors` array — `raise_for_status()` alone won't
catch them; always inspect `errors` (the helper does). Common messages:

- `Validation error (FieldUndefined@...) : Field 'foo' ... is undefined` — you invented a field. Check
  [../references/QUERIES.md](../references/QUERIES.md) or introspect: `{ __type(name:"File"){ fields { name } } }`.
- `Validation error (MissingFieldArgument@[participants]) : Missing field argument 'phs_accession'` —
  per-study queries **require** `phs_accession`. Resolve it via `studies` first
  ([../references/ENTITIES.md](../references/ENTITIES.md)).

## Two things to remember

- **Every field is a String** — even counts/sizes come back as strings on record nodes
  (`number_of_participants: "1102"`). The dedicated `*Count` queries return real ints. Cast as needed.
- **`first` defaults to 10.** Set it explicitly or you silently get 10 rows. See
  [paginate.md](paginate.md).

## No auth, ever (for metadata)

There is no API key, token, or header — all GC metadata/search is open-access (see [../auth.yaml](../auth.yaml)).
The API does **not** download data: controlled data needs dbGaP authorization and files are accessed on
the Cancer Genomics Cloud (CGC) by Velsera. See [files_for_study.md](files_for_study.md).
</content>
