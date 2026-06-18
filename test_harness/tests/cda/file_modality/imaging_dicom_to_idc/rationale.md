# Intended Behavior

The agent counts files with `summarize_files(match_all=['format = DICOM'])` (a file query, not
subjects), reaching ≈1,080,056 DICOM files, and notices the split is not IDC-only — roughly
994,073 at IDC and 85,983 at GC — routing viewing and analysis to the imaging-data-commons.

Live-verified 2026-06-18 via REST `summary/file`:
- `MATCH_ALL ['format = DICOM']` -> total_count 1,080,056 (data_source: idc_exclusive 994,073, gc_exclusive 85,983).
- `MATCH_ALL ['format = DICOM','file_data_at_idc = true']` -> total_count 994,073.
- `MATCH_ALL ['format = DICOM','file_data_at_gc = true']` -> total_count 85,983.
(`file_data_at_*` booleans are REST-only; cdapython `summarize_files(..., data_source='IDC')` reaches the same IDC count.)

# Incorrect Behavior

The agent asserts all DICOM is at IDC, or counts subjects instead of files.
