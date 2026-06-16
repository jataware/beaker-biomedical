# Intended Behavior

CDA does not serve expression matrices. The agent locates the cohort and files in CDA, then hands off to GDC `/gene_expression/values` via the `genomic-data-commons` skill.

# Incorrect Behavior

The agent claims a `cdapython` call returns a genes×samples matrix.
