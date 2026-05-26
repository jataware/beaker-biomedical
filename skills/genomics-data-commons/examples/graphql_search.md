# GraphQL: cases with file counts

The `/v0/graphql` endpoint lets you compose multi-level joins in a single round trip. Here we ask
for a small sample of cases plus per-case file totals and category breakdowns — three things that
would otherwise need three REST calls.

## Example

```python
import requests

query = """
query CaseFileCounts($filters: FiltersArgument) {
  viewer {
    repository {
      cases {
        hits(first: 5, filters: $filters) {
          total
          edges {
            node {
              case_id
              submitter_id
              primary_site
              files { hits(first: 0) { total } }
              summary {
                experimental_strategies { experimental_strategy file_count }
                data_categories { data_category file_count }
              }
            }
          }
        }
      }
    }
  }
}
"""

variables = {
    "filters": {
        "op": "in",
        "content": {"field": "cases.primary_site", "value": ["Kidney"]},
    }
}

r = requests.post(
    "https://api.gdc.cancer.gov/v0/graphql",
    json={"query": query, "variables": variables},
)
r.raise_for_status()

result = r.json()["data"]["viewer"]["repository"]["cases"]["hits"]
print("total kidney cases:", result["total"])
for edge in result["edges"]:
    n = edge["node"]
    print(n["submitter_id"], n["primary_site"],
          "files=", n["files"]["hits"]["total"])
    for s in n["summary"]["experimental_strategies"]:
        print("  ", s["experimental_strategy"], s["file_count"])
```

For schema discovery (what fields can `Case` return?):

```graphql
{ __type(name: "Case") { name fields { name } } }
```
