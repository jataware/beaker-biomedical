# Intended Behavior

The agent confirms the cohort has proteomics in CDA — `summarize_files(match_all=['format = mzML'])` (≈46,792 PDC files) or `subject_data_at_pdc = true` — and collects the PDC-resident subjects and files. Because CDA is metadata-only and holds no abundance values, protein quantitation hands off to `proteomic-data-commons` (GraphQL at `proteomic.datacommons.cancer.gov/graphql`): discover the study, then build a per-study log-ratio quant matrix, yielding a tumor-vs-normal protein matrix CDA cannot produce.

# Incorrect Behavior

The agent routes protein abundance to GDC, or claims CDA returns quantitation values.
