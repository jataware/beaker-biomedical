# Intended Behavior

The agent interprets "highly/most expressed" the way the GDC Data Portal does — most *variably* expressed — calling `POST /gene_expression/gene_selection` with `gene_type = "protein_coding"`, ranking by the standard deviation of `log2(uqfpkm)`, and explicitly stating it reports variability, not absolute level. For TCGA-LUAD the top genes are the lung-characteristic surfactant/secretory set PGC, SFTPC, BPIFA1, SFTPA1, SFTPA2, SCGB3A1, S100P, SCGB3A2, FGG, SPINK1; the top gene by variability (PGC) is not the highest by median, which confirms the ranking is by variability.

# Incorrect Behavior

The agent interprets "highly expressed" as absolute or median level (surfacing housekeeping genes) or pulls `/gene_expression/values` and ranks by mean, uses the wrong endpoint, or fails to disclose that the ranking is by variability.
