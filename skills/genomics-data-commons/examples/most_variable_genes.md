# "Highly expressed" genes for a cohort — matching the GDC Data Portal

When a user asks *"what genes are highly / most expressed in \<cancer\>?"*, the GDC Data Portal
answers with the most **variably** expressed genes — ranked by the standard deviation of
`log2(uqfpkm + 1)` across the cohort — **not** by the highest absolute or median expression level.
This is the least-surprise interpretation: absolute level is dominated by ubiquitously-high
housekeeping genes (mitochondrial, ribosomal, structural) that are high in *every* tissue and tell you
nothing about the cohort, whereas the variable genes are the ones that actually distinguish samples and
that the Portal's gene-expression view surfaces.

Use `POST /gene_expression/gene_selection` — it ranks by stddev for you. **Apply this interpretation
and tell the user** you ranked by expression *variability* (Portal behavior); if they specifically want
absolute level, compute it from `/gene_expression/values` instead (see the bottom of this file).

## Example — most variable genes in breast cancer

```python
import requests

# Scope the cohort in case_filters; gene_type=protein_coding is the Portal's gene universe
# (only protein-coding genes have expression data). selection_size = how many top genes to return.
body = {
    "case_filters": {"op": "in", "content": {"field": "cases.primary_site", "value": ["Breast"]}},
    "gene_type": "protein_coding",
    "selection_size": 10,
}
r = requests.post("https://api.gdc.cancer.gov/gene_expression/gene_selection",
                  headers={"Content-Type": "application/json"}, json=body)
r.raise_for_status()

for g in r.json()["gene_selection"]:          # already sorted by stddev, descending
    print(f"{g['symbol']:>8}  stddev={g['log2_uqfpkm_stddev']:.2f}  median={g['log2_uqfpkm_median']:.2f}")
```

Output — `SCGB2A2` is the single most variably expressed gene in breast, matching the Portal 1:1
(current data release; exact values drift between releases):

```
 SCGB2A2  stddev=4.00  median=4.95
 SCGB1D2  stddev=3.71  median=4.01
    TFF1  stddev=3.65  median=6.05
     PIP  stddev=3.58  median=5.27
  CALML5  stddev=3.00  median=2.31
     LTF  stddev=3.00  median=4.78
    TFF3  stddev=2.99  median=5.98
   MUCL1  stddev=2.93  median=1.62
    AGR3  stddev=2.86  median=6.11
   FDCSP  stddev=2.86  median=1.65
```

The response object carries `gene_id`, `symbol`, `log2_uqfpkm_median`, and `log2_uqfpkm_stddev` per gene
(it is **not** a bare `[{"gene_id": …}]` array — it's wrapped in a `gene_selection` key). Note SCGB2A2's
median (4.95) is *lower* than TFF1's (6.05) or AGR3's (6.11) — it wins on **variability**, not level,
which is exactly why ranking by absolute expression would give a different (and less useful) list.

A saved cohort or a single project works the same way — swap `case_filters` to
`cases.project.project_id` (e.g. `["TCGA-BRCA"]`, which also returns SCGB2A2 #1), `cases.disease_type`,
or use `cohort_id`. `min_median_log2_uqfpkm` (default 1) drops low-expression genes before ranking; raise
it to demand the variable genes also be reasonably expressed.

## Then: pull the matrix for those genes

Feed the selected `gene_id`s into `/gene_expression/values` to get the actual per-case matrix for a
heatmap — see [get_gene_expression_matrix.md](get_gene_expression_matrix.md).

```python
gene_ids = [g["gene_id"] for g in r.json()["gene_selection"]]
# then POST gene_ids + the same case collection to /gene_expression/values
```

## If the user really means absolute level

If they explicitly want the *highest-expressed* genes (not the most variable), there's no single
endpoint for it — pull `/gene_expression/values` with `tsv_units=uqfpkm` for the gene set of interest
and rank rows by mean/median across cases yourself. Expect housekeeping genes to dominate; say so, and
confirm that's what they wanted rather than the Portal's variability view.
