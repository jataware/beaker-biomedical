# Cohort API

A separate sub-API for creating named, persistable cohorts that other endpoints (gene expression,
mutation frequency) can reference by `cohort_id`. Base URL: `https://api.gdc.cancer.gov/v0`.

## Authentication

The Cohort API uses **cookie-based context**, not `X-Auth-Token`. Every cohort exists within a
context identified by a `gdc_context_id` cookie.

- First call to `POST /v0/cohorts` without a cookie: server creates a new context and returns
  `gdc_context_id` in the response `Set-Cookie` header.
- Subsequent calls must include that cookie.
- The context key can be downloaded (`GET /v0/cohorts/context/download`) for safe-keeping and
  uploaded later (`POST /v0/cohorts/context/upload`) to resume that context from another client.

In Python with `requests.Session`:

```python
import requests
s = requests.Session()
r = s.post("https://api.gdc.cancer.gov/v0/cohorts",
           headers={"Content-Type": "application/json"},
           json={"name": "Bladder cancer cohort",
                 "filters": {"op":"=","content":{"field":"cases.primary_site","value":"bladder"}},
                 "type": "static"})
# Session now carries the gdc_context_id cookie automatically.
```

## Endpoints

| Method | Path | Notes |
|---|---|---|
| POST | `/v0/cohorts` | Create. Body: `{name, filters, type: "static" \| "dynamic"}`. Query `delete_existing=true` to replace a name dup. |
| GET | `/v0/cohorts` | List. `?include_case_ids=true` to expand the case-id arrays. |
| GET | `/v0/cohorts/{cohort-id}` | Read one. |
| PUT | `/v0/cohorts/{cohort-id}` | Update. Body shape matches POST. |
| DELETE | `/v0/cohorts/{cohort-id}` | Delete. |
| POST | `/v0/cohorts/{cohort-id}/refresh-snapshot` | Re-evaluate a `dynamic` cohort against current data. |
| GET | `/v0/cohorts/context/download` | Download the binary `gdc_context_id` key. |
| POST | `/v0/cohorts/context/upload` | Upload a key file; server sets the cookie. |

## Cohort object

```json
{
  "id": "6a46a89b-66f5-4082-84b9-839abb71eb68",
  "name": "Bladder cancer cohort",
  "filters": { "op": "=", "content": { "field": "cases.primary_site", "value": "bladder" } },
  "type": "static",
  "case_ids": ["...uuid...", "..."],
  "data_release": { "id": "49f14b16-2775-4c27-8089-bfd58660e865" },
  "created_datetime": "2022-11-04T21:38:53Z",
  "modified_datetime": "2022-11-04T21:38:53Z"
}
```

`case_ids` is only populated when you ask for it (`?include_case_ids=true` on GET, or always on POST
response).

## Static vs dynamic

- **`static`** (default): the case list is frozen at creation time, identified by `case_ids`.
  Subsequent data releases that add/remove cases matching the filter do not change the cohort.
- **`dynamic`**: the filter is the source of truth; case list re-evaluates against the current data
  release. Use `refresh-snapshot` to materialize the current snapshot.

## Filter shape

Cohort `filters` are the same JSON shape as `/cases` filters — see
[FILTERS.md](FILTERS.md). Common: filter on `cases.project.project_id`, `cases.primary_site`,
`cases.disease_type`, `cases.demographic.*`.

## Using a cohort in other endpoints

Once you have a `cohort_id`, you can drop it into endpoints that accept cohort references:

- `/gene_expression/availability`, `/values`, `/gene_selection`
- `/analysis/top_mutated_genes`, `/top_ssms`, `/top_ssms_by_gene`

```json
{ "cohort_id": "6a46a89b-66f5-4082-84b9-839abb71eb68", "gene_ids": ["ENSG00000141510"], "selection_size": 50 }
```

## Common errors

- `400` with `cohort name is not unique` — pass `delete_existing=true` or pick a different name.
- `401` on update/delete — the cookie is missing or the context doesn't own this cohort.
- `404` on GET — cohort doesn't exist or your context can't see it.
