# Paginate a full result set

GC list queries take `first` (page size, **default 10**, **max 10000**) and `offset` (default 0). There
is **no `pagination`/`total` object** in the response — drive the loop off **page length** (stop on a
short page), and use the matching `*Count` query when you need an exact total. See
[../references/PAGINATION.md](../references/PAGINATION.md).

## Generic loop (stop on a short page)

```python
import requests
URL = "https://general.datacommons.cancer.gov/v1/graphql/"

def gc(query, tries=3):
    for _ in range(tries):
        b = requests.post(URL, json={"query": query}, timeout=120).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        if b.get("data") is not None: return b["data"]
    raise RuntimeError("GC returned null data")

def paginate(make_query, query_field, page=5000):
    """make_query(offset, first) -> GraphQL selecting `query_field` as a list. page <= 10000."""
    out, offset = [], 0
    while True:
        rows = gc(make_query(offset, page))[query_field]
        out.extend(rows)
        offset += page
        if len(rows) < page:          # short/empty page = last page
            return out

# Every participant in a study (1112 of them -> needs paging beyond the default 10):
participants = paginate(
    lambda o, f: '{ participants(phs_accession:"phs001287" offset:%d first:%d) { participant_id sex } }' % (o, f),
    query_field="participants")
print(len(participants))   # 1112

# Every study in GC:
studies = paginate(
    lambda o, f: '{ studies(offset:%d first:%d) { phs_accession study_name study_acronym } }' % (o, f),
    query_field="studies")
print(len(studies))        # ~89
```

## Confirm with a count query

```python
total = gc('{ participantsCount(phs_accession:"phs001287") }')["participantsCount"]  # real int: 1112
assert len(participants) == total
```

## Notes

- **`first` ≤ 10000.** For a node larger than that, the loop above pages through it; keep `page` modest
  (1000–5000) for snappy responses.
- **No total in the payload** — `*Count` queries (`participantsCount`, `filesCount`, …) give the total;
  they need `phs_accession` for per-study nodes.
- **The default page is 10** — never rely on it; always pass `first`.
- All scalar values are **Strings**; cast as needed.
</content>
