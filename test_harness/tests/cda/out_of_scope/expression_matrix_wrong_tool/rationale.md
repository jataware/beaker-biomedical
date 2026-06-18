# Intended Behavior

CDA is metadata-only and does not serve expression matrices. The agent locates the TCGA-BRCA cohort in CDA — `summarize_subjects(match_all=['project_short_name = TCGA-BRCA'], data_source='GDC')` returns 1,098 subjects (verified 2026-06-18) — then hands off the FPKM-UQ matrix request to GDC `/gene_expression/values` via the `genomic-data-commons` skill.

# Incorrect Behavior

The agent claims a `cdapython` call returns a genes×samples matrix.
