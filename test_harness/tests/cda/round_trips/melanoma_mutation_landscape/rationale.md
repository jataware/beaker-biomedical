# Intended Behavior

The agent locates the cohort in CDA with `summarize_subjects(match_all=['diagnosis = *melanoma*'], data_source='GDC')` (in cdapython 2.1.0 the `subject_data_at_gdc` boolean is not a searchable column, so `data_source='GDC'` is the correct handle; the boolean works only in raw REST `MATCH_ALL`), reaching 1,239 subjects (verified 2026-06-18) with ids like `TCGA.TCGA-FS-A1Z7` and `FM.AD12384`. It strips the `PROGRAM.` prefix to recover the GDC `cases.submitter_id` (`TCGA.TCGA-FS-A1Z7` → case `TCGA-FS-A1Z7` → project TCGA-SKCM), then computes mutation frequencies in GDC via the `genomic-data-commons` skill — not CDA's `mutation` table, whose counts are unreliable. Skin spans several projects (TCGA-SKCM 148, FM-AD 321, HCMI-CMDC 48, …), and `top_mutated_genes_by_project` for TCGA-SKCM returns TP53, CSMD3, CSMD1, TTN, CDKN2A, PLEC by raw count. A strong answer also notes the raw ranking is gene-size-biased and that the clinical drivers BRAF and NRAS surface through GDC's Cancer-Gene-Census plus cohort-denominator frequency recipe.

# Incorrect Behavior

The agent stays in CDA's mutation table for frequencies, or tunnel-visions on TCGA-SKCM and misses the other Skin projects.
