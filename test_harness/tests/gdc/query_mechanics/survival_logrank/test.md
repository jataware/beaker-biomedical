---
name: "Survival: log-rank requires an array of filters"
description: "This tests `POST /analysis/survival` semantics: a single `filters` object yields one curve and no p-value, while an array of two yields both curves plus the log-rank p-value, which the agent must read (not invent) and interpret."
---
Do male and female pancreatic cancer (TCGA-PAAD) patients differ in overall survival? Give me the p-value.
