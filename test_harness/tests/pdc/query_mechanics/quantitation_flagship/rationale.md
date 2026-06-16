# Intended Behavior

The agent reads `quantDataMatrix` (an un-paginated `log2_ratio` 2-D array that takes no GraphQL subfield selection), parses the `aliquot_id:aliquot_submitter_id` header, maps aliquots → cases → `sample_type` via `biospecimenPerStudy`, and drops QC/reference channels by `sample_type`. It concludes CA9 is higher in tumor (median `log2_ratio` ≈ +0.49 across 110 Primary Tumor vs ≈ −1.65 across 84 Solid Tissue Normal) and frames the value as a relative log2 ratio against the study's common reference, not an absolute amount.

# Incorrect Behavior

The agent describes the values as absolute abundance rather than relative log2 ratios, lets QC/reference channels (e.g. `QC5`, `sample_type = "Not Reported"`, cell lines) pollute the tumor/normal split — a "drop the unmapped" filter does not remove them — or reports the wrong direction.
