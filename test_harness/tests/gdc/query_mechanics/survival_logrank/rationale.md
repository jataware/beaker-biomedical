# Intended Behavior

The agent builds an array of two group filters (male and female within TCGA-PAAD) so `POST /analysis/survival` returns both curves plus the log-rank `overallStats` (pValue ≈ 0.366; male 101 / female 83), reads the p-value rather than inventing one, and concludes the difference is not statistically significant. A single `filters` object would yield one curve of 184 donors and an empty `overallStats` (no p-value), and the time axis is in days, not years.

# Incorrect Behavior

The agent passes a single `filters` object (or the whole cohort) and then fabricates a p-value where there is none, or claims a statistically significant difference when p ≈ 0.37 is not significant.
