# Intended Behavior

The agent finds the format with `column_values('format')` → `mzML`, counts ≈46,792 files (all at PDC) with `summarize_files(match_all=['format = mzML'])`, and notes CDA returns `drs_uri` only — quantitation is a `proteomic-data-commons` job, not GDC.

# Incorrect Behavior

The agent routes proteomics to GDC, or claims CDA itself computes abundances.
