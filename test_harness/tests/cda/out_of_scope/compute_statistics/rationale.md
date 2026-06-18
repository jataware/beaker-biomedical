# Intended Behavior

CDA is metadata-only and does no analysis — no Kaplan-Meier, no log-rank. The agent locates the two groups in CDA — within TCGA-LUAD, `sex = male` returns 261 subjects and `sex = female` returns 299 subjects (`summarize_subjects(match_all=['project_short_name = TCGA-LUAD', 'sex = male'/'sex = female'], data_source='GDC')`, verified 2026-06-18) — then routes the survival curve and log-rank p-value to GDC `/analysis/survival` via the `genomic-data-commons` skill.

# Incorrect Behavior

The agent claims to produce KM points or p-values from CDA, which is incorrect because CDA performs no analysis itself.
