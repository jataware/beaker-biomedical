# Intended Behavior

The agent uses, or self-corrects to, the canonical facet field `diagnoses.ajcc_pathologic_stage` and reports the four main TCGA-KIRC stages in the right ballpark (stage i 270, stage iii 125, stage iv 83, stage ii 60; keys are lowercase). The intuitive `diagnoses.tumor_stage` is invalid — it returns HTTP 200 with no `aggregations` and `warnings.facets = "unrecognized values: [diagnoses.tumor_stage]"` — so a good run inspects `warnings` and fixes the field rather than reporting an empty result.

# Incorrect Behavior

The agent facets on `diagnoses.tumor_stage` and reports an empty or zero breakdown because it never inspected `warnings`, or it treats the 200 response as success and silently returns nothing.
