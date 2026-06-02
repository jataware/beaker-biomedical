---
name: genomic-data-commons
description: >-
  Query, search, and download cancer genomics data from the NCI Genomic Data Commons (GDC) REST API.
  Use when the user needs to find cases or files in TCGA, TARGET, CPTAC, FM, BEATAML, HCMI, MMRF, CGCI,
  or other GDC programs; pull clinical, biospecimen, copy-number, or somatic-mutation metadata; download
  open-access files or generate Data Transfer Tool manifests; perform BAM slicing by gene or region;
  retrieve gene expression matrices (FPKM-UQ), top-mutated-genes/SSMs analyses, survival data, or scRNA-Seq
  expression; manage saved cohorts; or run ad-hoc GraphQL queries against the GDC schema.
compatibility: Python 3 with the `requests` package. No API key required for open-access data. Controlled-access downloads and submissions require GDC_TOKEN (an X-Auth-Token obtained from https://portal.gdc.cancer.gov/).
metadata:
  author: integrations
  source-integration:
  source-uuid:
---

# Genomic Data Commons (GDC) API

The NCI Genomic Data Commons API is the programmatic interface behind `portal.gdc.cancer.gov`. It exposes
harmonized cancer genomics datasets (TCGA, TARGET, CPTAC, BEATAML, HCMI, MMRF, CGCI, MATCH, …) for
search, retrieval, and download, plus analysis endpoints for gene expression, somatic mutations, copy
number variation, and survival.

**Base URL:** `https://api.gdc.cancer.gov`

Endpoint paths can optionally be version-pinned: `https://api.gdc.cancer.gov/v0/<endpoint>` resolves
to version 0. Unversioned paths track the current major version.

## Authentication

Authentication is **only** required for:

- Downloading controlled-access files (e.g. TCGA BAMs under `phs000178`).
- BAM slicing on controlled-access files.
- Submitting / updating data via the submission endpoints.

All open-access search, retrieval, analysis, and metadata endpoints work without a token.

When a token is required, pass it in the `X-Auth-Token` HTTP header:

```python
import os, requests
token = os.environ["GDC_TOKEN"]  # plain string from the user's downloaded token file
headers = {"X-Auth-Token": token}
r = requests.get("https://api.gdc.cancer.gov/data/fd89bfa5-b3a7-4079-bf90-709580c006e5", headers=headers)
```

Tokens expire — when a controlled-access call returns `{"error":"Your token is invalid or expired..."}`,
tell the user to download a fresh token from the GDC Data Portal.

## Critical rules

- **Treat the token as a credential.** Anyone holding it can download every controlled-access file the
  user has access to. Read it from `GDC_TOKEN` or a file path the user gives you; never embed it in code,
  never print it, never paste it into a shareable URL or example.
- **Use POST for non-trivial searches.** GET requests pass `filters` as a percent-encoded JSON string in
  the URL and break above ~8 KB. Always POST `application/json` for multi-clause filters or large
  `value:[...]` lists.
- **`size` defaults to 10.** If you do not set `size`, you will silently get only the first 10 hits, even
  when `total` is millions. Either set `size` explicitly or paginate with `from` / `size`.
- **The `manifest` endpoint ignores `size`.** It always returns the full match set. To cap a manifest, cap
  the upstream filter, not the request.
- **Tokens do not grant write access by default.** Submission requires the user be a registered submitter
  for the target project. If you are not sure, ask before calling any `submission/...` endpoint.
- **Do not invent fields.** Field names like `cases.demographic.sex_at_birth` are validated server-side;
  invalid fields return 400. When unsure, hit `<endpoint>/_mapping` to enumerate valid fields and field
  groups before constructing a filter. See [references/FIELDS.md](references/FIELDS.md).
- **Don't default to TCGA — discover the relevant projects first.** GDC holds ~90 projects across ~25
  programs; TCGA is only one program (33 projects). A disease or anatomical site almost always spans
  several programs — breast cases live in ~20 projects, leukemia in ~11 — and the TCGA project is rarely
  the largest (TARGET-AML has >10× the leukemia cases of TCGA-LAML). When the user names a cancer type,
  site, or cohort instead of an explicit `project_id`, enumerate the matching projects first (next
  section) and filter on the full set. Only narrow to a single project when the user names it.

## Discovering relevant projects

When the user describes data by disease, anatomical site, or clinical cohort rather than naming a
project, find the projects that actually match *before* building the query. The most reliable pattern
is to facet `/cases` by `project.project_id` using the same filter you will reuse downstream — the
counts are the real per-project match counts, and the bucket keys are the project set to query:

```python
import requests
# Which projects actually contain breast cases? (don't assume TCGA-BRCA)
r = requests.post("https://api.gdc.cancer.gov/cases",
    json={"filters": {"op": "in", "content": {"field": "primary_site", "value": ["Breast"]}},
          "facets": "project.project_id", "size": 0})
buckets = r.json()["data"]["aggregations"]["project.project_id"]["buckets"]
project_ids = [b["key"] for b in buckets]
# FM-AD 2583, TCGA-BRCA 1098, CMI-MBC 200, CPTAC-2 134, HCMI-CMDC 69, ... — 20 projects, not 1
```

Then filter the real `/files` or `/cases` query on `project_ids`. Other entry points: query `/projects`
filtered by `primary_site`/`disease_type` (project-level view; note its `summary.case_count` is the
whole-project total, not your filtered count), or `/v0/all?query=<term>` for free-text lookup. Full
strategies, the program catalogue, and caveats are in [references/PROJECTS.md](references/PROJECTS.md);
a worked discover-then-query recipe is in
[examples/discover_projects_for_disease.md](examples/discover_projects_for_disease.md).

## Endpoint catalogue

### Search & retrieval (open-access metadata)

| Endpoint | Returns | Notes |
|---|---|---|
| `/projects` | Projects (highest level) | One row per study (TCGA-BRCA, TARGET-NBL, …) |
| `/projects/{project_id}` | Single project metadata | Supports `expand=summary,summary.experimental_strategies,summary.data_categories` |
| `/cases` | Cases (patients/donors) | Filterable on `cases.*`, `demographic.*`, `diagnoses.*`, `samples.*` |
| `/cases/{case_id}` | Single case | UUID lookup |
| `/files` | Files | Most common entry point; filter on `cases.*` and `files.*` together |
| `/files/{file_id}` | Single file metadata | Only resolves the latest version |
| `/files/ids` | Lookup by `file_id`, `file_name`, or `submitter_id` | |
| `/files/versions` / `/files/versions/{file_ids}` | Version provenance for one-or-more files | Works on older versions too |
| `/files/versions/manifest` | Version info from an uploaded DTT manifest | POST `Content-Type: text/tsv` |
| `/history/{file_id}` | Full version + data-release history of a file | |
| `/annotations` / `/annotations/{annotation_id}` | Curator annotations | E.g. "Item flagged DNU" |
| `/<endpoint>/_mapping` | Field discovery | Returns `_mapping`, `defaults`, `expand`, `fields`, `multi`, `nested` |
| `/v0/all?query=<term>` | Quicksearch across cases/files/projects/genes/SSMs/annotations | |
| `/status` | API version & status | |
| `/v0/notifications` | User-facing system notifications | |

### Download

| Endpoint | Behavior |
|---|---|
| `/data/{file_ids}` | GET or POST. Single UUID → file body; comma-separated UUIDs or POST `{"ids":[...]}` → `.tar.gz`. Append `?related_files=true` to bundle BAI/TBI. Append `?tarfile` for uncompressed tar. |
| `/manifest/{file_ids}` | Generates a DTT-compatible manifest. Also: append `&return_type=manifest` to any `/files` query. |
| `/slicing/view/{file_id}` | Remote BAM slicing by region (`region=chr1:10000-20000`) or gene (`gencode=BRCA1`). Slices have no `.bai` — index with `samtools index`. |

### Analysis (open-access)

| Endpoint | Returns |
|---|---|
| `/genes`, `/genes/{gene_id}` | Gene summary by Ensembl ID |
| `/ssms`, `/ssms/{ssm_id}` | Simple somatic mutations |
| `/ssm_occurrences`, `/ssm_occurrences/{id}` | SSMs joined to cases |
| `/cnvs`, `/cnvs/{cnv_id}`, `/cnvs/ids` | Gene-level copy-number variation |
| `/cnv_occurrences`, `/cnv_occurrences/{id}`, `/cnv_occurrences/ids` | CNVs joined to cases |
| `/segment_cnvs`, `/segment_cnv_occurrences` | Segment-level CNVs |
| `/analysis/top_cases_counts_by_genes` | Per-project case counts for a gene list (no `format`/`fields`) |
| `/analysis/top_mutated_genes_by_project` | Most-mutated genes in a project |
| `/analysis/top_mutated_cases_by_gene` | Most-affected cases for given genes |
| `/analysis/mutated_cases_count_by_project` | Cases with any SSM per project |
| `/analysis/survival` | Raw data for survival plots |
| `/analysis/top_mutated_genes` | TSV: top mutated genes for a cohort/filter |
| `/analysis/top_ssms` | TSV: top SSMs for a cohort/filter |
| `/analysis/top_ssms_by_gene` | TSV: top SSMs within a single gene context (requires `gene_id`) |
| `/analysis/top_ssms_by_case` | TSV: top SSMs for a case in its project (requires `case_id`) |

See [references/MUTATION-FREQUENCY.md](references/MUTATION-FREQUENCY.md) for TSV column definitions.

### Gene expression

| Endpoint | Purpose |
|---|---|
| `/gene_expression/availability` | Does FPKM-UQ data exist for these cases/genes? |
| `/gene_expression/values` | TSV matrix: genes × cases (`uqfpkm` or `median_centered_log2_uqfpkm`) |
| `/gene_expression/gene_selection` | Top-N most variably expressed genes for a case collection |
| `/scrna_seq/gene_expression` | scRNA-Seq per-cell expression for one case/file × up to 10 genes |

See [references/GENE-EXPRESSION.md](references/GENE-EXPRESSION.md) and
[references/SCRNA-SEQ.md](references/SCRNA-SEQ.md).

### Cohorts (separate API, requires cookie context)

`POST /v0/cohorts` to create, `GET /v0/cohorts/{id}` to read, `POST /v0/cohorts/{id}/refresh-snapshot`
to re-evaluate a dynamic cohort. The cohort API uses a `gdc_context_id` cookie rather than X-Auth-Token.
See [references/COHORTS.md](references/COHORTS.md).

### GraphQL

- Search & retrieval: `POST https://api.gdc.cancer.gov/v0/graphql`
- Submission: `POST https://api.gdc.cancer.gov/v0/submission/graphql`

Schema is introspectable via `{ __schema { types { name kind } } }`. See
[references/GRAPHQL.md](references/GRAPHQL.md).

### Submission

`POST/PUT/DELETE https://api.gdc.cancer.gov/submission/<Program>/<Project>` — only available to
registered submitters; requires `X-Auth-Token`. See [references/SUBMISSION.md](references/SUBMISSION.md).

## Filter syntax

The `filters` parameter is a nested JSON object of operators and `{field, value}` operands. The same
shape is used everywhere — `/files`, `/cases`, `/annotations`, `/ssms`, analysis endpoints, cohort
definitions.

```json
{"op":"and","content":[
  {"op":"in","content":{"field":"cases.project.project_id","value":["TCGA-BRCA"]}},
  {"op":"=", "content":{"field":"files.data_type","value":"Gene Expression Quantification"}}
]}
```

Operators: `=`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `exclude`, `excludeifany`, `is` (missing), `not`
(missing), `and`, `or`. Wildcards (`*`) are supported in `value`.

**`exclude` vs `excludeifany`:** for list-valued fields like `diagnoses.classification_of_tumor`,
`exclude` drops a record only when *every* element matches; `excludeifany` drops it when *any* element
matches. They behave identically for scalar fields.

See [references/FILTERS.md](references/FILTERS.md) for the full operator table and worked examples.

## Common query parameters

| Parameter | Default | Description |
|---|---|---|
| `filters` | null | JSON filter object (see above) |
| `format` | `JSON` | Also `TSV` or `XML` |
| `fields` | server defaults | Comma-separated field list. `id` is always included. |
| `expand` | null | Comma-separated field-group names from `/_mapping` `expand` list |
| `size` | **10** | Hits per page. Set explicitly. |
| `from` | 0 | Offset for pagination |
| `sort` | null | `field:asc` or `field:desc` |
| `facets` | null | Aggregate counts; pair with `size=0` |
| `pretty` | false | Indent JSON output |
| `return_type` | null | Set to `manifest` on `/files` queries to get a DTT manifest |

## Response shape

```json
{
  "data": {
    "hits": [ { "id": "uuid", "...": "..." } ],
    "pagination": {
      "count": 10, "total": 931947, "size": 10,
      "from": 0, "page": 1, "pages": 93195
    }
  },
  "warnings": {}
}
```

- `pagination.total` is the matched-record count — use it to plan paginated retrieval.
- For aggregate (`facets`) queries the response also carries `data.aggregations.<field>.buckets[]`.
- Errors come back as `{"error": "...", "message": "..."}` with a 4xx/5xx code.

## Gotchas

- **`access` field.** `"access":"open"` = downloadable without a token. `"access":"controlled"` =
  needs a token + project authorization (dbGaP `acl` value such as `phs000178`). Filter on
  `files.access` when you only want open data.
- **Project IDs are case-sensitive and dash-separated.** `TCGA-BRCA`, not `tcga_brca`.
- **Don't default to TCGA — a disease or site spans many projects.** Discover the full project set
  before filtering. See [Discovering relevant projects](#discovering-relevant-projects) and
  [references/PROJECTS.md](references/PROJECTS.md).
- **`cases.project.project_id` ≠ `project_id`.** From the `/files` endpoint, project lives on the
  case; from `/projects`, it's top-level. Mirror the data model.
- **`/files/{file_id}` only resolves the *latest* version of a file.** For older versions, use
  `/files/versions/{file_ids}` or `/history/{file_id}`.
- **BAM slices have no .bai.** Run `samtools index` after downloading.
- **`size=0` + `facets=…`** is the right pattern for "give me counts, no records."
- **Facet names are field names — invalid ones return 200, not 400.** An unknown facet like
  `diagnoses.tumor_stage` (a common TCGA-era hallucination; the canonical field is
  `diagnoses.ajcc_pathologic_stage`) comes back with no `aggregations` key and a
  `warnings.facets: "unrecognized values: [...]"`. Inspect `warnings` on every facet call. Consult
  [references/FACETS.md](references/FACETS.md) or `<endpoint>/_mapping` before guessing a facet name.
- **`return_type=manifest` ignores `size`.** It dumps every match.
- **Quicksearch base64-encodes ids.** `/v0/all` returns an extra base64 `id` field alongside the real
  `case_id`/`file_id`/`project_id`. Use the real id for follow-up calls.
- **GraphQL search endpoint is `/v0/graphql`** (not `/graphql`). There is no unversioned alias.
- **The `annotations` endpoint is also reachable at the (typo'd) path `/annotatations/_mapping`** — that
  alias appears in the official OpenAPI spec but the canonical path is `/annotations/_mapping`.
- **`filters` on the cohort API differs from `case_filters` on analysis endpoints.** Analysis endpoints
  (top_mutated_genes, etc.) accept *both* `filters` (defining the cohort) and `case_filters` (defining
  the case universe within the cohort). Don't conflate them.
- **`expand` on `/cases` is the only way to surface nested arrays** (`diagnoses`, `samples`,
  `samples.portions`, …) at full fidelity. Without `expand`, you only get the scalar fields on `case`.

## Example usage

The smallest useful query — get one file's metadata by UUID, no auth needed:

```python
import requests
r = requests.get("https://api.gdc.cancer.gov/files/cb92f61d-041c-4424-a3e9-891b7545f351",
                 params={"pretty": "true"})
print(r.json()["data"])
```

For complete worked examples see [examples/](examples/):

- [discover_projects_for_disease.md](examples/discover_projects_for_disease.md) — Find every project for a disease, then query them (don't default to TCGA).
- [search_files_by_project.md](examples/search_files_by_project.md) — Find RNA-Seq files in TCGA-BRCA.
- [download_file_by_uuid.md](examples/download_file_by_uuid.md) — Single-file and batch download.
- [download_set_via_manifest.md](examples/download_set_via_manifest.md) — Search → manifest → DTT.
- [query_case_with_diagnoses.md](examples/query_case_with_diagnoses.md) — Pull a case with nested clinical data.
- [discover_fields_mapping.md](examples/discover_fields_mapping.md) — Use `/_mapping` to find valid fields.
- [facet_aggregation.md](examples/facet_aggregation.md) — Count cases by `primary_site` with `facets=` + `size=0`.
- [get_gene_expression_matrix.md](examples/get_gene_expression_matrix.md) — FPKM-UQ matrix.
- [top_mutated_genes.md](examples/top_mutated_genes.md) — Cohort-level mutation analysis.
- [bam_slice_by_gene.md](examples/bam_slice_by_gene.md) — Pull BRCA1 reads from a BAM.
- [graphql_search.md](examples/graphql_search.md) — A GraphQL `cases` query.
- [survival_analysis.md](examples/survival_analysis.md) — Survival curve data.

## References

- [references/PROJECTS.md](references/PROJECTS.md) — How to discover which projects match a disease,
  site, or cohort (so you don't default to TCGA); program catalogue; `summary.case_count` caveat. Load
  before scoping a query when the user named a cancer type rather than a `project_id`.
- [references/FILTERS.md](references/FILTERS.md) — Filter operators, wildcards, `is missing`, nested
  list semantics, full payload examples. Load when constructing or debugging a `filters` object.
- [references/ENDPOINTS.md](references/ENDPOINTS.md) — Full endpoint table with HTTP methods and
  request/response shapes. Load when you need an endpoint not summarized above.
- [references/FIELDS.md](references/FIELDS.md) — How to use `/_mapping`, `defaults`, `expand`, and
  `nested`; common field groupings (`cases.demographic.*`, `cases.diagnoses.*`, `analysis.*`). Load
  before composing a fields/filter list.
- [references/FACETS.md](references/FACETS.md) — Curated facet field names per endpoint, the
  `warnings.facets` failure mode, and a verification recipe. Load when constructing a `facets=`
  query, or after a facet call comes back with no aggregations.
- [references/DOWNLOADING.md](references/DOWNLOADING.md) — Single + batch download, manifests,
  controlled-access, related_files, BAM slicing details.
- [references/GENE-EXPRESSION.md](references/GENE-EXPRESSION.md) — `/gene_expression/{availability,values,gene_selection}`:
  payloads, response shapes, the 120k-data-point cap.
- [references/MUTATION-FREQUENCY.md](references/MUTATION-FREQUENCY.md) — TSV column dictionaries for
  `/analysis/top_mutated_genes`, `top_ssms`, `top_ssms_by_gene`, `top_ssms_by_case`.
- [references/ANALYSIS.md](references/ANALYSIS.md) — `/genes`, `/ssms`, `/cnvs`, segment CNVs,
  `/analysis/survival`, observations.
- [references/SCRNA-SEQ.md](references/SCRNA-SEQ.md) — Single-cell RNA-Seq endpoint behavior and limits.
- [references/COHORTS.md](references/COHORTS.md) — `/v0/cohorts` API and the `gdc_context_id` cookie.
- [references/GRAPHQL.md](references/GRAPHQL.md) — GraphQL endpoints, introspection, sample queries.
- [references/SUBMISSION.md](references/SUBMISSION.md) — Submission API, templates, dictionary,
  transactions, dry runs.

The original upstream OpenAPI specs are preserved verbatim in [assets/](assets/):
`gdcapi.yaml`, `cohortapi.yaml`, `gene-expression.yaml`, `mutation-frequency.yaml`,
`scrna-seq-gene-expression.yaml`.
