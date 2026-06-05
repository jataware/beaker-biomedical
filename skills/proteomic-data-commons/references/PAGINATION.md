# Pagination

PDC has two families of "list" queries, and they paginate differently.

## Queries that REQUIRE `offset` + `limit`

All `getPaginated*` and `*PerStudy` queries (and `getPaginatedPublications`) require both `offset` and
`limit` as arguments. Omit them and you get a GraphQL error or a tiny default — not the full set.

- `offset` — 0-based row offset.
- `limit` — page size. **Hard cap 25000** (documented on `fileMetadata`; treat it as the ceiling
  everywhere). Large pages on `*PerStudy` / `filesPerStudy` queries can be slow.

These queries return a `pagination` block alongside the data:

```json
"pagination": { "count": 100, "sort": "", "from": 0, "page": 1, "total": 1423, "size": 100, "pages": 15 }
```

- `total` — total matching rows.
- `pages` — number of pages at the current `size`.
- `count` / `size` — rows on this page / requested page size.

### Don't drive the loop off `pagination.total` — it is frequently null (verified)

Under load, PDC commonly returns the **list field fully populated but `pagination` itself `null`** (no
`errors`, HTTP 200) — observed repeatedly on `getPaginatedCases`. If your loop reads
`pagination["total"]` you'll crash on a `NoneType` mid-run. **Drive the loop off the page length
instead: stop when a page returns fewer rows than `limit`.** This is robust whether or not
`pagination` comes back, and it's the canonical pattern for this API.

```python
import time, requests
URL = "https://proteomic.datacommons.cancer.gov/graphql"

def _post(query, tries=5):
    """POST with retry on the transient null-data responses PDC emits under load."""
    for k in range(tries):
        body = requests.post(URL, json={"query": query}, timeout=180).json()
        if body.get("errors"):
            raise RuntimeError(body["errors"])
        data = body.get("data")
        if data and all(v is not None for v in data.values()):
            return data
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

def paginate(make_query, list_key, query_field, page_size=1000):
    """make_query(offset, limit) -> GraphQL string. Stops on a short page (no pagination.total dep)."""
    offset, rows = 0, []
    while True:
        payload = _post(make_query(offset, page_size))[query_field]
        page = payload[list_key]                 # the list field (e.g. "cases")
        rows.extend(page)
        offset += page_size
        if len(page) < page_size:                # short/empty page = last page
            return rows
```

Example:

```python
cases = paginate(
    lambda o, l: '{ getPaginatedCases(offset: %d limit: %d) { cases { case_submitter_id disease_type } } }' % (o, l),
    list_key="cases", query_field="getPaginatedCases")
```

See [examples/paginate_cases.md](../examples/paginate_cases.md).

## Queries that take `offset`/`limit` literally in the query body but don't require args

`allCases` and `getPaginatedGenes` embed `offset`/`limit` in their documented query text. `allCases`
with the baked-in `offset:0 limit:10` returns 10 rows; edit those literals (or pass them) to page
through. The docs note you can call `allCases` without paging to retrieve all ~6,200 cases, but that
is a heavy call — prefer `getPaginatedCases` with a loop.

## Queries with NO pagination (whole result in one call)

`quantDataMatrix`, `clinicalPerStudy`, `biospecimenPerStudy`, `studyExperimentalDesign`,
`experimentalMetadata`, `allPrograms`, `diseasesAvailable`, `tissueSitesAvailable`, etc. return their
full result in a single response. For `quantDataMatrix` and `clinicalPerStudy` this can be large and
slow — there is no way to cap it from the request, so the lever is choosing a smaller study. See
[QUANTITATION.md](QUANTITATION.md).

## Performance notes

- Several bulk queries are flagged in the docs as *"may take a long time to execute because of the
  huge volume of data"* (`filesPerStudy`, `paginatedCase*PerStudy`). Use modest page sizes and POST.
- `geneSpectralCount`, `aliquotSpectralCount`, and `protein` *"may return slowly or time out the first
  time due to data volume; the result is cached and returns promptly on retry with the same
  parameters."* If a first call times out, simply retry.
