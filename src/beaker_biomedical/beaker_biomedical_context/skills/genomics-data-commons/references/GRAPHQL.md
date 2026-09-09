# GraphQL endpoints

GDC exposes two GraphQL endpoints. Both accept `POST` with `Content-Type: application/json`. They
return the **same** data as REST — the underlying source is identical — but GraphQL lets you ask for
arbitrary subsets in a single round trip.

| Endpoint | Use |
|---|---|
| `https://api.gdc.cancer.gov/v0/graphql` | Search & retrieval (open access). Mirrors `/projects`, `/cases`, `/files`, `/ssms`, `/cnvs`, etc. |
| `https://api.gdc.cancer.gov/v0/submission/graphql` | Query **submitted but unreleased** data. Released data is not visible here — use the search endpoint instead. Requires X-Auth-Token. |

The GDC has no unversioned `/graphql` route — always include `/v0`.

For interactive exploration, point [GraphiQL](https://github.com/graphql/graphiql) at the endpoint
URL.

## Request shape

```json
{ "query": "<graphql-string>",
  "variables": { "filters_1": {"op":"in","content":{...}} } }
```

Variables are passed as a JSON object alongside the query string. They are GDC-typed (the SDL has
`FiltersArgument`, `Int`, `String`, …).

## Two ways to query

**Option 1: introspection.** Useful for discovery.

```graphql
{ __schema { types { name kind fields { name } } } }
```

```graphql
{ __type(name: "Case") { name fields { name } } }
```

**Option 2: nodes + edges.** This is the actual query pattern.

```graphql
query PROJECTS_EDGES($filters_1: FiltersArgument) {
  projects {
    hits(filters: $filters_1) {
      total
      edges {
        node {
          primary_site
          disease_type
          project_id
          dbgap_accession_number
        }
      }
    }
  }
}
```

Variables:

```json
{ "filters_1": {"op":"in","content":{"field":"projects.primary_site","value":["Kidney"]}} }
```

## Common query patterns

### Case + file counts

```graphql
query CaseFileCounts($filters: FiltersArgument) {
  viewer {
    repository {
      cases {
        hits(first: 1, filters: $filters) {
          edges {
            node {
              case_id
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
```

### SSMs by gene

```graphql
query SsmsByGene($filters_2: FiltersArgument) {
  explore {
    ssms {
      hits(filters: $filters_2) {
        total
        edges { node { ssm_id gene_aa_change } }
      }
    }
  }
}
```

Variables:

```json
{ "filters_2": {"op":"in","content":{"field":"consequence.transcript.gene.gene_id","value":["ENSG00000155657"]}} }
```

## Sending from Python

```python
import requests
query = """
query Q($f: FiltersArgument) {
  cases { hits(first: 5, filters: $f) { total edges { node { case_id submitter_id primary_site } } } }
}
"""
variables = {"f": {"op":"=","content":{"field":"cases.primary_site","value":"Lung"}}}
r = requests.post("https://api.gdc.cancer.gov/v0/graphql",
                  json={"query": query, "variables": variables})
r.raise_for_status()
print(r.json()["data"]["cases"]["hits"]["total"])
```

## When to prefer GraphQL over REST

- You want a **subset** of deeply nested fields across multiple entity types in one round trip.
- You want join-style queries (e.g. "for each case, total file count plus a summary breakdown").
- You're prototyping / exploring a new field — GraphiQL introspection is faster than reading
  `/_mapping`.

Stick with REST when:

- You want a bulk dump of all data on an entity (`expand` + `fields`).
- You need TSV/XML output (GraphQL is JSON-only).
- You need to use `facets` for aggregations — the REST API is more ergonomic here.

## Mutations (submission GraphQL)

Mutation operations on `/v0/submission/graphql` parallel the REST `PUT/POST/DELETE` operations under
`/submission/<Program>/<Project>`. They require an `X-Auth-Token` from a submitter account. See
[SUBMISSION.md](SUBMISSION.md). The GDC documentation does not cover mutation usage in detail — refer
to the schema via introspection.
