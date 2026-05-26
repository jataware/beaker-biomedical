# GDC endpoint reference

Base URL: `https://api.gdc.cancer.gov`. Version-pinned: `/v0/...`.

## Status / metadata

| Method | Path | Notes |
|---|---|---|
| GET | `/status` | `{commit, status, tag, version}` |
| GET | `/v0/notifications` | INFO/WARNING/ERROR/DEBUG messages per component |
| GET | `/v0/all?query=<term>&size=<n>` | Quicksearch across cases/files/projects/genes/SSMs/annotations |

## Projects

| Method | Path | Body / query | Returns |
|---|---|---|---|
| GET / POST | `/projects` | `filters`, `fields`, `size`, `from`, `sort`, `facets`, `format`, `pretty`, `expand` | List of projects |
| GET | `/projects/{project_id}` | `expand=summary,summary.experimental_strategies,summary.data_categories` | Single project + summary |
| GET | `/projects/_mapping` | — | Field discovery |

## Cases

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/cases` | Same parameter set as `/files`. Use `expand=diagnoses,demographic,samples,...` for nested clinical fields. |
| GET / POST | `/cases/{case_id}` | Single case by UUID. `expand=diagnoses` etc. |
| GET | `/cases/_mapping` | Field discovery |

## Files

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/files` | `filters`, `fields`, `size`, `from`, `sort`, `facets`, `format`, `expand`, `pretty`. Append `&return_type=manifest` to get a DTT manifest. |
| GET / POST | `/files/{file_id}` | Latest version only |
| GET / POST | `/files/ids` | Lookup by `file_id`, `file_name`, or `submitter_id` |
| GET | `/files/versions/{file_ids}` | `file_ids` is comma-separated; returns current+latest version pair per ID |
| GET | `/files/versions` | Variant — accepts payload of IDs |
| POST | `/files/versions/manifest` | Body: a DTT manifest TSV (`Content-Type: text/tsv`, `--data-binary`) |
| GET | `/history/{file_id}` | Full release history |
| GET | `/files/_mapping` | Field discovery |

## Annotations

| Method | Path | Notes |
|---|---|---|
| GET / POST | `/annotations` | Filter on `entity_id`, `entity_type` |
| GET | `/annotations/{annotation_id}` | Single annotation |
| GET | `/annotations/_mapping` | Field discovery. (The OpenAPI spec also lists the typo path `/annotatations/_mapping` — both resolve.) |

## Download

| Method | Path | Notes |
|---|---|---|
| GET | `/data/{file_ids}` | Single UUID → file body; comma-separated UUIDs → `.tar.gz`. Append `?related_files=true` for BAI/TBI. Append `?tarfile` for uncompressed tar. Add `X-Auth-Token` for controlled-access. |
| POST | `/data` | Body `{"ids":["uuid","uuid"]}` (JSON) or `ids=uuid&ids=uuid` (form). |
| GET | `/manifest/{file_ids}` | DTT manifest from a UUID list. |
| POST | `/manifest` | Same shape as `/data` POST. |
| GET / POST | `/slicing/view/{file_id}` | BAM slicing. Query: `region=chr1:10000-20000` or `region=unmapped` or `gencode=BRCA1`. JSON body: `{"regions":[...], "gencode":[...]}`. Requires `X-Auth-Token` for controlled BAMs. |

## Analysis (open-access)

| Method | Path | Notes |
|---|---|---|
| GET | `/genes`, `/genes/{gene_id}` | Use `expand=...` to surface transcripts/canonical info |
| GET | `/ssms`, `/ssms/{ssm_id}` | Simple somatic mutations. Use `expand=occurrence.case.observation.read_depth` for MAF-style detail. |
| GET | `/ssm_occurrences`, `/ssm_occurrences/{id}` | SSMs joined to cases |
| GET | `/cnvs`, `/cnvs/{cnv_id}`, `/cnvs/ids?query=<cnv_id>` | Gene-level CNV |
| GET | `/cnv_occurrences`, `/cnv_occurrences/{id}`, `/cnv_occurrences/ids` | CNVs joined to cases |
| GET | `/segment_cnvs`, `/segment_cnv_occurrences` | Segment-level CNVs |
| GET / POST | `/analysis/top_cases_counts_by_genes` | Per-project case counts for a gene list. **No** `format`/`fields` support. |
| GET / POST | `/analysis/top_mutated_genes_by_project` | |
| GET / POST | `/analysis/top_mutated_cases_by_gene` | |
| GET / POST | `/analysis/mutated_cases_count_by_project` | |
| GET / POST | `/analysis/survival` | Raw points for survival plots; payload includes `filters` |

## Mutation Frequency (cohort-based TSV downloads)

All four endpoints support GET and POST and return `text/tab-separated-values`. Both `X-Auth-Token`
header and cookie auth schemes are accepted (cookie used by the Portal; header preferred for scripts).

| Method | Path | Required input |
|---|---|---|
| GET / POST | `/analysis/top_mutated_genes` | one of: `filters`, `case_filters`, `cohort_id` |
| GET / POST | `/analysis/top_ssms` | one of: `filters`, `case_filters`, `cohort_id` |
| GET / POST | `/analysis/top_ssms_by_gene` | `gene_id` + cohort definition |
| GET / POST | `/analysis/top_ssms_by_case` | `case_id` |

Common optional fields: `attachment` (`true`/`false`, sets Content-Disposition), `filename`,
`downloadCookieKey`, `downloadCookiePath`.

See [MUTATION-FREQUENCY.md](MUTATION-FREQUENCY.md) for column definitions.

## Gene Expression

| Method | Path | Body / response |
|---|---|---|
| POST | `/gene_expression/availability` | `{case_ids[], case_set_id, cohort_id, case_filters, gene_ids[], gene_set_id}` (any one cases collection, any one genes collection, or both). Response: per-case and per-gene `has_gene_expression_values` booleans. |
| POST | `/gene_expression/values` | Same collections + `format=tsv\|json`, `tsv_units=uqfpkm\|median_centered_log2_uqfpkm`. TSV matrix: rows=genes, cols=cases. **Cap: 120 000 data points (cases × genes).** |
| POST | `/gene_expression/gene_selection` | Cases collection + genes collection + `selection_size`. Optional `min_median_log2_uqfpkm` (default 1). Returns the top `selection_size` most variable genes (sorted by std-dev of log2(uqfpkm+1) after filtering on median). |

Genes are identified by Ensembl gene IDs matching `^ENSG\d{11}$`. Only protein-coding genes have
expression data.

## scRNA-Seq

| Method | Path | Body |
|---|---|---|
| POST | `/scrna_seq/gene_expression` | `{case_id\|file_id, gene_ids[]}` — exactly one of case_id/file_id, max 10 genes per call |

Returns per-cell expression values. See [SCRNA-SEQ.md](SCRNA-SEQ.md).

## Cohorts (separate API)

Base: `https://api.gdc.cancer.gov/v0`. Auth: `gdc_context_id` **cookie**, not X-Auth-Token.

| Method | Path | Notes |
|---|---|---|
| POST | `/cohorts` | `{name, filters, type: static\|dynamic}`. Query `delete_existing=true` to clobber name dupes. |
| GET | `/cohorts` | `include_case_ids=true` to expand case lists. |
| GET / PUT / DELETE | `/cohorts/{cohort-id}` | |
| POST | `/cohorts/{cohort-id}/refresh-snapshot` | Re-evaluate a dynamic cohort against current data. |
| GET | `/cohorts/context/download` | Download the context-key file. |
| POST | `/cohorts/context/upload` | Upload a context-key file (sets the cookie). |

See [COHORTS.md](COHORTS.md).

## GraphQL

| Method | Path | Use |
|---|---|---|
| POST | `/v0/graphql` | Search/retrieval queries. Introspect with `{__schema{types{name kind}}}`. |
| POST | `/v0/submission/graphql` | Query unreleased/in-flight submitted data. |

See [GRAPHQL.md](GRAPHQL.md).

## Submission

Auth: `X-Auth-Token`. User must be registered for the target project.

| Method | Path | Use |
|---|---|---|
| PUT / POST / DELETE | `/submission/{Program}/{Project}` | Create / update / delete entities |
| `/submission/{Program}/{Project}/_dry_run` | Append to URL to simulate without writes |
| GET | `/v0/submission/template/{entity}?format=json\|tsv\|csv` | Download a submission template |
| GET | `/v0/submission/_dictionary/_all` | All entity JSON schemas |
| GET | `/v0/submission/_dictionary/{entity}` | One entity's schema |

See [SUBMISSION.md](SUBMISSION.md).
