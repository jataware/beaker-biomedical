# Expect

- **CDA locate:** `get_subject_data(match_all=['diagnosis = *melanoma*', 'subject_data_at_gdc = true'])`
  → **≈ 1,229 subjects** with ids like `TCGA.TCGA-FS-A1Z7`, `FM.AD12384`.
- **↳ Hand-off key:** strip the `PROGRAM.` prefix → GDC `cases.submitter_id`. Verified:
  `TCGA.TCGA-FS-A1Z7` → GDC case `TCGA-FS-A1Z7` → project **TCGA-SKCM** (Skin/“Nevi and Melanomas”).
- **GDC analyze** (`genomic-data-commons`): Skin spans multiple projects — **TCGA-SKCM 148, FM-AD 321,
  HCMI-CMDC 48, …** (don't default to TCGA); `top_mutated_genes_by_project` for TCGA-SKCM →
  **TP53, CSMD3, CSMD1, TTN, CDKN2A, PLEC** (raw count-ranked).
- **Why hand off / grading nuance:** mutation frequency is a GDC product (CDA's `mutation` table has
  unreliable counts). A strong agent also notes the raw ranking is gene-size-biased and that the
  clinical melanoma drivers (**BRAF, NRAS**) surface via GDC's Cancer-Gene-Census + cohort-denominator
  frequency recipe (`genomic-data-commons` → `examples/top_mutated_genes.md`).

# Failure Cases

- **Fail signs:** stays in CDA's mutation table for frequencies; tunnel-visions on TCGA-SKCM and misses
  the other Skin projects.

# Automated Checks

```yaml
checks:
  - number:
      name: "melanoma_gdc_subjects"
      target: 1229
      tolerance_percent: 15
  - behavior: "located the cohort in CDA, stripped the PROGRAM. prefix to get GDC cases.submitter_id, then computed frequencies in GDC (genomic-data-commons), NOT CDA's mutation table"
  - substring: "TCGA-SKCM"
  - set_contains:
      name: "top_genes"
      members: ["TP53", "CDKN2A"]
  - behavior: "did not default to only TCGA-SKCM (noted Skin spans FM-AD / HCMI-CMDC / … other projects)"
  - must_not_contain: ["mutation frequencies from CDA", "CDA's mutation table for the ranking"]
```
