# Pagination

Every GC Data Type Query (the list queries: `studies`, `participants`, `files`, …) takes two pagination
arguments. Pagination is **required** in the sense that the defaults will silently truncate you.

- **`first`** — page size. **Defaults to 10.** Maximum **10000**. If you omit it you get only the first
  10 records even when the study has thousands.
- **`offset`** — 0-based number of records to skip. Defaults to 0.

There is **no `pagination`/`total` object** in the Data Type Query responses (unlike PDC). To know how
many records exist, call the matching **count query** first; to retrieve everything, **loop until a page
returns fewer than `first` rows**.

## The default-10 footgun

```graphql
{ participants(phs_accession: "phs001287") { participant_id } }      # ❌ returns 10, not all 1102
{ participants(phs_accession: "phs001287" first: 10000) { participant_id } }   # ✓ up to 10000
```

A study with `number_of_participants: "1102"` returns 10 participants unless you raise `first`. Always
set `first` explicitly, and page when the count exceeds 10000.

## Size a study with the count queries

Per-study counts are cheap and tell you whether one page suffices:

```graphql
{ participantsCount(phs_accession: "phs001287")
  filesCount(phs_accession: "phs001287")
  samplesCount(phs_accession: "phs001287") }
```

`first` maxes at 10000, so any node with a count above that needs a loop.

## Loop pattern (stop on a short page)

```python
import requests
URL = "https://general.datacommons.cancer.gov/v1/graphql/"

def gc(query, tries=3):
    for _ in range(tries):
        body = requests.post(URL, json={"query": query}, timeout=120).json()
        if body.get("errors"):
            raise RuntimeError(body["errors"])
        if body.get("data") is not None:
            return body["data"]
    raise RuntimeError("GC returned null data")

def paginate(make_query, query_field, page=5000):
    """make_query(offset, first) -> GraphQL string selecting `query_field` as a list. page <= 10000."""
    out, offset = [], 0
    while True:
        rows = gc(make_query(offset, page))[query_field]
        out.extend(rows)
        offset += page
        if len(rows) < page:        # short/empty page = last page
            return out

participants = paginate(
    lambda o, f: '{ participants(phs_accession:"phs001287" offset:%d first:%d) { participant_id sex race } }' % (o, f),
    query_field="participants")
print(len(participants))
```

## Notes

- **`first` ≤ 10000.** A larger value is rejected. Use a loop for big nodes; modest pages (1000–5000)
  keep responses snappy.
- **No total in the payload** — drive loops off page length, and use the `*Count` queries when you need
  an exact total up front.
- All scalar values come back as **String** (e.g. `file_size: "25920500"`) — cast as needed.
</content>
