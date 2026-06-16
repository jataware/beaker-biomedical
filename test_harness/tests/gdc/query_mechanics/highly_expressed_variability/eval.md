# Expect

**most _variably_ expressed**, ranked by the standard deviation of `log2(uqfpkm)` via
`POST /gene_expression/gene_selection` with `gene_type = "protein_coding"` — and that it *says* it is
reporting variability, not absolute level.
**Expected result (verified ground truth):**
- `gene_selection` (cohort = `cases.project.project_id in ["TCGA-LUAD"]`, `gene_type=protein_coding`,
  `selection_size=10`) returns, sorted by stddev descending:
  **PGC, SFTPC, BPIFA1, SFTPA1, SFTPA2, SCGB3A1, S100P, SCGB3A2, FGG, SPINK1** — lung-characteristic
  surfactant/secretory genes. The response is wrapped in a `gene_selection` key with per-gene
  `symbol`, `log2_uqfpkm_stddev`, `log2_uqfpkm_median`.
- The top gene by variability (PGC, stddev ≈ 3.63) does **not** have the highest median — SFTPA2
  (median ≈ 8.89) and SFTPA1 (median ≈ 8.66) are far higher in absolute level — confirming the ranking
  is by variability, not level.
**Pass:** calls `/gene_expression/gene_selection` (protein-coding), returns a list dominated by the
lung-specific genes above, AND explicitly states the ranking is by expression *variability* (Portal
behavior), offering absolute level as a different computation.

# Failure Cases

**Trap(s):**
1. Interpreting "highly expressed" as absolute/median expression level (which would surface
   housekeeping genes), or pulling `/gene_expression/values` and ranking by mean.
2. Using the wrong endpoint, or not disclosing that the ranking is by variability.
**Fail:** returns a housekeeping/ubiquitous-gene list, claims to report absolute expression level
without caveat, or invents an endpoint.

# Automated Checks

```yaml
checks:
  - set_contains:
      name: "top_genes"
      members: ["SFTPC", "SFTPA1", "SFTPA2"]
  - substring_any: ["SFTPC", "SFTPA1", "SFTPA2", "PGC", "SCGB3A2"]
  - count_at_least:
      name: "genes_returned"
      min: 5
  - substring_any: ["variab", "standard deviation", "stddev", "most variably expressed"]
  - behavior: "called /gene_expression/gene_selection with gene_type=protein_coding (ranked by stddev), not absolute-level from /gene_expression/values"
  - must_not_contain: ["absolute abundance", "absolute expression level"]
```
