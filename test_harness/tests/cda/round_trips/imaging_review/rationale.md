# Intended Behavior

The agent locates the glioblastoma cohort's DICOM files in CDA with a file query such as
`summarize_files(match_all=['format = DICOM', 'diagnosis = Glioblastoma'], data_source='IDC')`
or `get_file_data(match_all=['format = DICOM', 'diagnosis = Glioblastoma'], data_source='IDC')`,
returning file rows that carry `drs_uri`. CDA returns the `drs_uri`, never pixels; the imaging
series and viewers live at the imaging-data-commons (IDC). The agent should hand the user off to
the imaging-data-commons to actually open a viewer, not claim CDA can render or download the images.

Live-verified 2026-06-18 (REST `summary/file` MATCH_ALL ['format = DICOM','file_data_at_idc = true','diagnosis = Glioblastoma']
and cdapython `summarize_files(match_all=['format = DICOM','diagnosis = Glioblastoma'], data_source='IDC')`):
- 11,113 DICOM files at IDC for diagnosis = Glioblastoma, across 1,478 subjects.
- Includes 3,957 MR Image Storage (radiology), plus Segmentation, Slide Microscopy, Annotation, Parametric Map.
- `diagnosis` is title-case (`Glioblastoma`); `format` is uppercase (`DICOM`).
This is a real, non-trivial imaging cohort; the prompt names it concretely so the agent need not ask "which cohort?".

# Incorrect Behavior

The agent expects CDA to render or download the images, or stops to ask which cohort is meant
instead of running the glioblastoma DICOM query.
