# Intended Behavior

The agent enumerates projects via a `/cases` facet on `project.project_id` under a `primary_site in ["Kidney"]` filter (`size=0`), finding 16 projects and 2,436 kidney cases. It names the largest as a non-TCGA project — TARGET-WT 652 — above TCGA-KIRC 537, FM-AD 408, TCGA-KIRP 291, and CPTAC-3 261, and reports per-project counts in the right ballpark. A follow-up on `disease_type` must use GDC's lowercase ICD-O-style vocabulary (`adenomas and adenocarcinomas`, …); the title-case string returns 0.

# Incorrect Behavior

The agent returns only TCGA projects (defaulting to TCGA) or a single number, or it filters `disease_type = "Clear Cell Renal Cell Carcinoma"` in title case, silently gets 0, and stops instead of discovering the lowercase vocabulary.
