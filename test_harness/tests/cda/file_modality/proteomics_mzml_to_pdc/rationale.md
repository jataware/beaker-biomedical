# Intended Behavior

The agent finds the format with `column_values('format')` → `mzML`, counts ≈46,792 files (all at PDC) with `summarize_files(match_all=['format = mzML'])`, and notes CDA returns `drs_uri` only — quantitation is a `proteomic-data-commons` job, not GDC.

# Incorrect Behavior

The agent routes proteomics to GDC, or claims CDA itself computes abundances.

# Live verification (2026-06-18)

- mzML files total = **46,792**
  `summarize_files(match_all=['format = mzML'], return_data_as='dataframe_list')[0]['number_of_matching_files']`
- All 46,792 are at PDC; GDC/IDC/GC/ICDC = 0
  `summarize_files(match_all=['format = mzML'], data_source='PDC')` = 46792; same with `data_source='GDC'` (etc.) = 0
- The `file` table returns `drs_uri` and no abundance/quantitation column (cols: file_id, access, anatomic_site, category, drs_uri, file_description, file_name, file_type, format, size, tumor_vs_normal, data_source).
- Checks: `number` (count, ±15%); three `behavior` claims split out of the former compound — (a) counted via a file query on `format = mzML`, (b) routed quantitation to proteomic-data-commons, (c) noted drs_uri-only / no abundances. The routing destination and the false-capability trap (GDC routing / CDA computing) are all left to the `behavior` judge — there is no `substring_any`/`must_not_contain` here, because those would either assume wording or false-fail a correct answer that negates ("CDA doesn't compute…").
