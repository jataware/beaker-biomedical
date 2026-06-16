---
name: "Melanoma mutation landscape (CDA → GDC) ✅ fully verified both sides"
description: "This tests the full CDA→GDC round-trip: locate the melanoma+genomic cohort in CDA, strip the `PROGRAM.` prefix to a GDC `cases.submitter_id`, and compute mutation frequencies in GDC (not CDA's mutation table)."
---
Find the melanoma patients that also have genomic data, and tell me the most frequently mutated genes for them.
