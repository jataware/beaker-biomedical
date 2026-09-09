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

## Cancer Gene Census default

Like the GDC Data Portal's mutation-frequency view, default these endpoints to the Cancer Gene Census
by adding `genes.is_cancer_gene_census = "true"` to `filters` (value is the **string** `"true"`), and
**tell the user you applied it** — the result is census-only and they can lift it. `and` it with the
cohort definition:

```json
{"op":"and","content":[
  {"op":"=", "content":{"field":"genes.is_cancer_gene_census","value":"true"}},
  {"op":"in","content":{"field":"cases.project.project_id","value":["TCGA-BRCA"]}}
]}
```

Skip the default (and the notice) when the user already constrained `is_cancer_gene_census` or asked
for all genes. This is the mutation-frequency instance of the cross-endpoint convention in
[ANALYSIS.md → Cancer Gene Census default](ANALYSIS.md#cancer-gene-census-default--applies-across-gene-centric-endpoints);
note the field path here is `genes.is_cancer_gene_census`, which differs from the path on `/ssms`,
`/cnvs`, and `/genes` itself.

## POST body example — top_mutated_genes

```json
{
  "case_filters": {
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

The cohort goes in `case_filters` (not `filters`) so the percentage denominator is the cohort's
SSM-tested case count — see [`case_filters` vs `filters`](#case_filters-vs-filters--and-the-frequency-denominator).

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

## `case_filters` vs `filters` — and the frequency denominator

These are **not interchangeable**, even though both accept a cohort-shaped filter document. They drive
different parts of the percentage:

- **`case_filters` defines the case universe** — the denominator `num_cohort_ssm_cases` ("cohort cases
  tested for SSM"). Scope your cohort here.
- **`filters` restricts the ranked entity** (which SSMs/genes appear as rows) and does **not** shrink
  the denominator.

Pass your cohort as `filters` instead of `case_filters` and the denominator stays at the GDC-wide total
(currently **18,289** cases tested for SSM), so cohort percentages collapse to nonsense:

| Cohort passed as | gene / cohort | affected / `num_cohort_ssm_cases` | cohort % |
|---|---|---|---|
| `filters` (wrong) | TP53 / TCGA-ACC | 15 / **18,289** | 0.08% |
| `case_filters` (right) | TP53 / TCGA-ACC | 15 / **90** | **16.67%** |

The right-hand denominator (90) is exactly the count of TCGA-ACC cases with
`available_variation_data = ssm` — the same number the GDC Data Portal uses. **Scope the cohort with
`case_filters` whenever you care about frequencies.** Reserve `filters` for genuinely restricting which
mutations are *ranked* (e.g. only HIGH-impact SSMs) while keeping the full case universe as the
denominator.

## Validating the denominator against the Portal

`num_cohort_ssm_cases` = cases in the cohort with `available_variation_data = ssm`; `num_gdc_ssm_cases`
is the same count GDC-wide (18,289). **Both `*_percentage` columns are already in percent units** (e.g.
`16.67`, not `0.1667`) — do not multiply by 100 again.

`available_variation_data` is **not** a field on the REST `/cases` (repository) index — it lives on the
GDC **explore** case index. Reach it via GraphQL `explore { cases }` (field
`cases.available_variation_data`), or as `case.available_variation_data` on `/genes` and
`/ssm_occurrences` (`occurrence.case.available_variation_data` on `/ssms`). To reproduce a Portal
denominator exactly:

```python
import requests
q = "query($f: FiltersArgument){ explore { cases { hits(case_filters:$f, first:0){ total } } } }"
f = {"op": "and", "content": [
        {"op": "in", "content": {"field": "cases.available_variation_data", "value": ["ssm"]}},
        {"op": "in", "content": {"field": "cases.project.project_id", "value": ["TCGA-ACC"]}}]}
r = requests.post("https://api.gdc.cancer.gov/v0/graphql", json={"query": q, "variables": {"f": f}})
print(r.json()["data"]["explore"]["cases"]["hits"]["total"])   # 90 — equals num_cohort_ssm_cases
```

## Reproducing the Portal's gene table (the default recipe)

The GDC Data Portal's per-cohort gene table = a **Cancer-Gene-Census-filtered ranking over the
cohort's SSM-tested cases**. Reproduce it 1:1 by filling both filter slots — `case_filters` for the
cohort (the denominator), `filters` for the census default (apply it and tell the user):

```python
body = {
  "case_filters": {"op": "in", "content": {"field": "cases.primary_site", "value": ["kidney"]}},
  "filters":      {"op": "=",  "content": {"field": "genes.is_cancer_gene_census", "value": "true"}},
}
```

Kidney result — denominator `num_cohort_ssm_cases` = **1035**, matching the Portal exactly:

| Rank | Gene | Cases | % |
|---|---|---|---|
| 1 | VHL | 343 | 33.14 |
| 2 | PBRM1 | 243 | 23.48 |
| 3 | MUC16 | 96 | 9.28 |
| 4 | SETD2 | 92 | 8.89 |
| 5 | BAP1 | 89 | 8.60 |
| 6 | TP53 | 61 | 5.89 |
| 7 | MTOR | 58 | 5.60 |

**The census filter sets eligibility, not rank.** Order is always by cohort mutation frequency, so a
famous census gene can sit mid-list (TP53 is #6 in kidney — VHL/PBRM1 are the renal drivers, TP53 is
rare in RCC) and a large passenger-prone gene can rank high (drop the filter and non-census TTN appears
at #3, 19.3%; MUC16 is the same kind of gene but is flagged census, so it survives the filter and
outranks TP53 by raw burden). Full walkthrough:
[../examples/top_mutated_genes.md](../examples/top_mutated_genes.md).

## Common workflow

```python
import requests, csv, io

# Top 20 mutated genes in TCGA-BRCA — cohort via case_filters so the denominator is
# the count of TCGA-BRCA cases tested for SSM, not the GDC-wide 18,289.
r = requests.post(
    "https://api.gdc.cancer.gov/analysis/top_mutated_genes",
    headers={"Content-Type": "application/json"},
    json={"case_filters": {"op": "in",
                           "content": {"field": "cases.project.project_id",
                                       "value": ["TCGA-BRCA"]}}},
)
r.raise_for_status()
reader = csv.DictReader(io.StringIO(r.text), delimiter="\t")
for row in list(reader)[:20]:
    # cohort_ssm_affected_cases_percentage is already in percent units (e.g. 34.16).
    print(row["symbol"], row["num_cohort_ssm_affected_cases"],
          f"{row['num_cohort_ssm_cases']} ({row['cohort_ssm_affected_cases_percentage']}%)")
```
