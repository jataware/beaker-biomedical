# Authoring a GraphQL / Bento-commons skill from live introspection

For a GraphQL commons (model on `skills/general-commons` / `skills/proteomic-data-commons`), where
the schema is the source of truth but **defined ≠ working**.

## 1. Introspect the live schema

```python
import requests
q = "{ __schema { queryType { fields { name } } } }"
r = requests.post("https://general.datacommons.cancer.gov/v1/graphql/", json={"query": q})
print([f["name"] for f in r.json()["data"]["__schema"]["queryType"]["fields"]])
```

This reveals query families the upstream docs (and any prior skill) miss — typically a
faceted-search layer (the cohort builder), structured record queries, and metrics/counts. Document
all the layers; the faceted layer is usually the primary researcher entry point, not "UI-only".

## 2. Probe each family — classify working vs erroring

```python
# Some Bento commons require a `variables` key even when empty, or the call errors "variables is null".
def gql(query, variables=None):
    return requests.post("https://general.datacommons.cancer.gov/v1/graphql/",
                         json={"query": query, "variables": variables or {}}).json()
```

Run one real query per family. On a prototype commons you may find the schema defines dozens of
queries while only the Elasticsearch-backed study-level ones answer and node-level queries error
with a dead-backend message. **Say so plainly in the skill** — present the working set as usable
and the rest as known-erroring, never the full schema as if it all works.

## 3. Capture the framework quirks as Critical rules

Things you can only learn by probing, each a one-line rule in `SKILL.md`:

- POST-only (a GET is rejected), or the mandatory `variables` key.
- Facet bucket count field is `cases`/`subjects`, not `count`.
- Files carry a CRDC DRS id (`dg.4DFC/<uuid>` → `drs://…`) for out-of-band download; the API never
  streams bytes.

## 4. Structure

`SKILL.md`: base URL, the layer map, the Critical-rule quirks, a query table, Gotchas, pointers.
`references/`: per-layer query detail + the field/facet catalogue. `examples/`: one runnable query
per layer with verified counts. `assets/`: the introspected SDL / backend `*.graphql` saved verbatim.
`auth.yaml`: `credentials: []` for an open metadata API, with the DRS/dbGaP download note.
