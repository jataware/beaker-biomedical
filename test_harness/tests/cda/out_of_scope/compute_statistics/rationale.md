# Intended Behavior

CDA does no analysis — no survival, no log-rank. The agent locates the cohort and its GDC-resident subset, and the curve and p-value come from GDC `/analysis/survival` via the `genomic-data-commons` skill.

# Incorrect Behavior

The agent claims to produce KM points or p-values from CDA, which is incorrect because CDA performs no analysis itself.
