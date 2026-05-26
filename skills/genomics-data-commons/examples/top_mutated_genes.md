# Top mutated genes in a project

`POST /analysis/top_mutated_genes` returns a TSV of genes ranked by the number of cases in a cohort
with at least one simple somatic mutation in that gene. The cohort is defined by a `filters` JSON
document, a `case_filters` document, or a saved `cohort_id`.

## Example

```python
import io, csv, requests

# Cohort = all TCGA-BRCA cases
body = {
    "filters": {
        "op": "in",
        "content": {"field": "cases.project.project_id",
                    "value": ["TCGA-BRCA"]},
    },
    "attachment": "false",
    "filename": "tcga-brca-top-mutated-genes.tsv",
}

r = requests.post(
    "https://api.gdc.cancer.gov/analysis/top_mutated_genes",
    headers={"Content-Type": "application/json"},
    json=body,
)
r.raise_for_status()

reader = csv.DictReader(io.StringIO(r.text), delimiter="\t")
for row in list(reader)[:20]:
    print(f"{row['symbol']:>10}  "
          f"{row['num_cohort_ssm_affected_cases']:>5}/{row['num_cohort_ssm_cases']}  "
          f"({float(row['cohort_ssm_affected_cases_percentage'])*100:.1f}%)")
```

Sample output:

```
      PIK3CA    348/986  (35.3%)
        TP53    314/986  (31.8%)
       TTN      147/986  (14.9%)
    ...
```

To rank SSMs *within* a single gene context, swap to `/analysis/top_ssms_by_gene` and add
`"gene_id": "ENSG00000141510"` to the body. To rank SSMs across the cohort regardless of gene, use
`/analysis/top_ssms`.
