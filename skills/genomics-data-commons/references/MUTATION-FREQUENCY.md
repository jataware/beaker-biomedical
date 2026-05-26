# Mutation Frequency API

Endpoints that produce TSV downloads describing the most mutated genes / SSMs (single somatic
mutations) within a cohort or context. All are reachable at `https://api.gdc.cancer.gov/analysis/...`
and accept both GET and POST.

| Endpoint | Required context | Description |
|---|---|---|
| `/analysis/top_mutated_genes` | one of `filters`, `case_filters`, `cohort_id` | Genes ranked by # cases in cohort with ≥1 SSM in that gene |
| `/analysis/top_ssms` | one of `filters`, `case_filters`, `cohort_id` | SSMs ranked by # cases in cohort carrying that SSM |
| `/analysis/top_ssms_by_gene` | cohort context + `gene_id` (ENSG…) | Top SSMs within a given gene |
| `/analysis/top_ssms_by_case` | `case_id` (UUID) | Top SSMs for one case in its project context |

## Request fields

| Field | Type | Notes |
|---|---|---|
| `filters` | object | GQL filters defining the cohort |
| `case_filters` | object | Same — alternative input |
| `cohort_id` | UUID string | A saved cohort from the Cohort API |
| `gene_id` | string `^ENSG\d{11}$` | Required for `top_ssms_by_gene` |
| `case_id` | UUID string | Required for `top_ssms_by_case` |
| `attachment` | `"true"`/`"false"` | If `true`, sets `Content-Disposition: attachment` |
| `filename` | string | Output filename; defaults to `top-mutated-genes.<YYYY>-<MM>-<DD>.tsv` etc. |
| `downloadCookieKey`, `downloadCookiePath` | strings | Used by the Portal's download-cookie pattern; safe to omit. |

Authentication accepted via `X-Auth-Token` header **or** cookie. Open-access mutation data does not
require a token, but cohort_id resolution against a private cohort does.

## POST body example — top_mutated_genes

```json
{
  "filters": {
    "op": "in",
    "content": {
      "field": "cases.project.project_id",
      "value": ["TCGA-BRCA"]
    }
  },
  "attachment": "true",
  "filename": "tcga-brca-top-mutated-genes.tsv"
}
```

```bash
curl -X POST 'https://api.gdc.cancer.gov/analysis/top_mutated_genes' \
  -H 'Content-Type: application/json' \
  --data @body.json \
  --output top_mutated_genes.tsv
```

## TSV columns

### `top_mutated_genes`

| Column | Meaning |
|---|---|
| `gene_id` | Ensembl gene ID |
| `symbol` | HUGO gene symbol |
| `name` | Gene name |
| `cytoband` | Chromosomal location(s) |
| `type` | Biotype |
| `num_cohort_ssm_affected_cases` | # cases in cohort with ≥1 SSM in gene |
| `num_cohort_ssm_cases` | # cases in cohort tested for SSM |
| `cohort_ssm_affected_cases_percentage` | ratio of above two |
| `num_gdc_ssm_affected_cases` | # cases across all of GDC with ≥1 SSM in gene |
| `num_gdc_ssm_cases` | # cases across all of GDC tested for SSM |
| `gdc_ssm_affected_cases_percentage` | ratio |
| `num_cohort_cnv_cases` | # cases in cohort tested for CNV |
| `num_cohort_cnv_gain_cases` / `_loss_cases` | counts |
| `cohort_cnv_gain_cases_percentage` / `_loss_cases_percentage` | ratios |
| `num_mutations` | total SSMs in gene |
| `annotations` | Cancer gene census tags |

### `top_ssms`

| Column | Meaning |
|---|---|
| `ssm_id` | Mutation UUID |
| `dna_change` | e.g. `chr5:g.14304578C>G` |
| `protein_change` | e.g. `TRIO L229V` |
| `type` | Mutation subtype |
| `consequence` | Canonical transcript consequence |
| `num_cohort_ssm_affected_cases` | # cases in cohort with this SSM |
| `num_cohort_ssm_cases` | # cases in cohort tested for SSM |
| `cohort_ssm_affected_cases_percentage` | ratio |
| `num_gdc_ssm_affected_cases` / `num_gdc_ssm_cases` / `gdc_ssm_affected_cases_percentage` | global versions |
| `vep_impact`, `sift_impact`, `sift_score`, `polyphen_impact`, `polyphen_score` | predicted-impact tools |

### `top_ssms_by_gene`

Same columns as `top_ssms` but `num_cohort_ssm_*` is replaced by `num_{GENE_ID}_*` (the cases tested
for SSMs filtered to the given gene context).

### `top_ssms_by_case`

Same columns as `top_ssms` but the cohort numerator uses the case's own project:
`num_{PROJECT_ID}_ssm_affected_cases` / `num_{PROJECT_ID}_cases`.

## Distinguishing `filters` and `case_filters`

Both define cohorts. The practical difference shows up when the endpoint composes its own implicit
filter (e.g., on `ssms.consequence`); `case_filters` is meant for "narrow the case universe" while
`filters` is meant for "filter on the entity being ranked." For most ad-hoc use the two are
interchangeable — if one returns an empty TSV, try the other.

## Common workflow

```python
import requests, csv, io

# Top 20 mutated genes in TCGA-BRCA
r = requests.post(
    "https://api.gdc.cancer.gov/analysis/top_mutated_genes",
    headers={"Content-Type": "application/json"},
    json={"filters": {"op": "in",
                       "content": {"field": "cases.project.project_id",
                                   "value": ["TCGA-BRCA"]}}},
)
r.raise_for_status()
reader = csv.DictReader(io.StringIO(r.text), delimiter="\t")
for row in list(reader)[:20]:
    print(row["symbol"], row["num_cohort_ssm_affected_cases"], row["cohort_ssm_affected_cases_percentage"])
```
