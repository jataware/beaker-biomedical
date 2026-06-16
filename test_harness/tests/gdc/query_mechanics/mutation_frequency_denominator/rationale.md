# Intended Behavior

The agent calls `top_mutated_genes` with the cohort in `case_filters` (which sets the denominator `num_cohort_ssm_cases` = 428 for TCGA-COAD) and the Cancer Gene Census in `filters` (`genes.is_cancer_gene_census = "true"`). It reports APC ≈72% (307/428), TP53 ≈55%, and KRAS ≈43%, and states explicitly that the list is Cancer-Gene-Census-only (the Portal default) and can be lifted.

# Incorrect Behavior

The agent puts the cohort in `filters` instead of `case_filters`, so the denominator stays the GDC-wide 18,289 and frequencies collapse to nonsense (APC reads 1.68%); reports raw counts with no denominator; or never mentions the census restriction.
