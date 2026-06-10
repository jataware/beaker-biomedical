# Pagination, ordering & node filters

## Default page size depends on the query family — this is a footgun

| Family | Default limit | To get more |
|---|---|---|
| Portal `*Overview`, `globalSearch` | **`first: 10`** | set `first`, loop `offset` |
| `searchCases` | not paged | returns counts + full ID arrays already |
| Auto-generated **node queries** (`case`, `file`, `sample`, …) | **no limit** (returns all) | set `first` to **cap** large nodes |
| Cypher convenience queries | varies; most accept `first`/`offset` | set `first` |

So `{ case { case_id } }` returns **all 1,029** cases, but `caseOverview` returns only 10 unless you
raise `first`. Decide per query.

## The paging arguments

- `first: Int` — page size. `offset: Int` — rows to skip. `order_by` + `sort_direction`
  (`"ASC"`/`"DESC"`) on the portal `*Overview` queries; `orderBy: String` on node/convenience queries
  (e.g. `orderBy: "file_size desc"`).

Loop until a page returns fewer than `first` rows:

```python
def page(query_tmpl, size=100):
    out, off = [], 0
    while True:
        rows = post(query_tmpl.format(first=size, offset=off))   # your POST helper
        out += rows
        if len(rows) < size:
            return out
        off += size
```

## Node-query `filter` operators

Every auto-generated node query accepts a `filter` object (input type `_<node>Filter`) in addition to
exact-match property args. For each property `X` the filter supports:

`X` (eq), `X_not`, `X_in: [..]`, `X_not_in: [..]`, `X_lt`/`X_lte`/`X_gt`/`X_gte`,
`X_contains`/`X_not_contains`, `X_starts_with`/`X_not_starts_with`, `X_ends_with`/`X_not_ends_with`,
`X_matches` (regex) — plus the boolean combinators `AND: [..]`, `OR: [..]`, `NOT: [..]`.

```graphql
# studies whose code is in a set, ordered, capped
{ study(filter: { clinical_study_designation_in: ["OSA01","OSA02","OSA03"] },
        orderBy: "clinical_study_designation", first: 10) {
    clinical_study_designation clinical_study_name clinical_study_type } }

# samples with a tumor over a size threshold, OR a specific site
{ sample(filter: { OR: [ { volume_of_tumor_gt: 10 }, { sample_site: "Bone" } ] }, first: 50) {
    sample_id sample_site volume_of_tumor } }
```

Discover a node's filter fields with `{ __type(name:"_caseFilter"){ inputFields { name } } }`.

Inline property args (e.g. `study(clinical_study_designation: "OSA01")`) are the shorthand for a single
equality and can be combined with `first`/`offset`/`orderBy`; reach for `filter` when you need ranges,
lists, substrings, or boolean logic.
