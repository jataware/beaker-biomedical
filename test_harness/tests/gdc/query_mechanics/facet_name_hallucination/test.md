---
name: "Facet-name hallucination (200, not 400)"
description: "This tests that the agent uses the canonical facet field and inspects `warnings`, since the invalid `diagnoses.tumor_stage` returns HTTP 200 with no aggregations (not a 400); the correct field is `diagnoses.ajcc_pathologic_stage`."
---
Break the TCGA-KIRC cases down by tumor stage.
