# GDC `filters` parameter

All search & retrieval endpoints, analysis endpoints, the `manifest` endpoint, and the cohort API accept
the same JSON-shaped `filters` document. The same document also defines a saved Cohort.

## Operators

| Operator | Meaning | Operands |
|---|---|---|
| `=` | equals (string or number) | 1 |
| `!=` | not equal | 1 |
| `<`, `<=`, `>`, `>=` | numeric comparison | 1 |
| `in` | value ∈ list | many |
| `exclude` | drop record only if **all** list elements of `field` match | many |
| `excludeifany` | drop record if **any** list element of `field` matches | many |
| `is` | `field is missing` | constant `"missing"` |
| `not` | `field not missing` | constant `"missing"` |
| `and` | logical AND of nested ops | many |
| `or` | logical OR of nested ops | many |

For scalar (non-list) fields, `exclude` and `excludeifany` produce identical results.

## Document shape

A leaf clause:

```json
{
  "op": "=",
  "content": { "field": "cases.demographic.sex_at_birth", "value": ["male"] }
}
```

A compound clause:

```json
{
  "op": "and",
  "content": [
    {"op":"in","content":{"field":"cases.submitter_id","value":["TCGA-CK-4948","TCGA-D1-A17N"]}},
    {"op":"=","content":{"field":"files.data_type","value":"Gene Expression Quantification"}}
  ]
}
```

`value` accepts a JSON string OR a JSON array — for `in` it must be an array; for `=` either is
accepted. Keep `value` always an array for consistency.

## Wildcards

`*` is supported in `value`:

```json
{"op":"=","content":{"field":"disease_type","value":"*Adenocarcinoma"}}
```

## `is missing` / `not missing`

```json
{"op":"is","content":{"field":"diagnoses.ajcc_pathologic_stage","value":"missing"}}
```

## Field names

`field` strings can be the endpoint-agnostic form (`cases.demographic.sex_at_birth`) or the
endpoint-specific form returned by `/_mapping`. Both are accepted in `filters`; only the
endpoint-specific form is guaranteed valid for `fields=`. When in doubt, GET `<endpoint>/_mapping` and
look in the `fields` block.

## GET vs POST

GET requests must percent-encode the JSON. There is no length limit specified by GDC, but practical
breakage starts around 8 KB. POST with `Content-Type: application/json` is the safer default for
anything more than a single-clause filter.

GET payload:

```
GET /cases?filters=%7B%22op%22%3A%22%3D%22%2C%22content%22%3A%7B%22field%22%3A%22cases.demographic.sex_at_birth%22%2C%22value%22%3A%5B%22male%22%5D%7D%7D
```

POST payload (same query):

```json
{
  "filters": {"op":"=","content":{"field":"cases.demographic.sex_at_birth","value":["male"]}},
  "fields": "submitter_id,case_id",
  "size": "100",
  "format": "TSV"
}
```

## Worked example: `exclude` vs `excludeifany`

Given a case `33165ed4-...` with two diagnoses — one `classification_of_tumor=metastasis`, one
`classification_of_tumor=primary`:

- `exclude diagnoses.classification_of_tumor=[metastasis]` → case is **kept** (not all diagnoses match).
- `excludeifany diagnoses.classification_of_tumor=[metastasis]` → case is **dropped** (one matches).

## Worked example: complex AND/OR

Female lung-cancer cases with at least one STAR-Counts file, open access:

```json
{
  "op": "and",
  "content": [
    {"op":"in","content":{"field":"cases.project.primary_site","value":["Lung"]}},
    {"op":"in","content":{"field":"cases.demographic.sex_at_birth","value":["female"]}},
    {"op":"in","content":{"field":"files.analysis.workflow_type","value":["STAR - Counts"]}},
    {"op":"in","content":{"field":"files.access","value":["open"]}}
  ]
}
```

## Facet + filter interaction

For the curated list of valid facet field names per endpoint and the `warnings.facets` failure mode,
see [FACETS.md](FACETS.md).

When `facets` and `filters` are combined:

1. The top-level operator in `filters` MUST be `and`.
2. Internal operators must be `=`, `!=`, `in`, `exclude`, `is`, or `not`.
3. The aggregation for a faceted field **ignores** any filter on that same field — this is the GDC
   Portal's "facet stays available when you have it selected" behavior.
