# Intended Behavior

The agent locates the DICOM files in CDA with `get_file_data(match_all=['format = DICOM'], data_source='IDC')`, returning file rows with `drs_uri` (≈994k DICOM at IDC). CDA returns the `drs_uri`, never pixels; series and viewers live at the imaging-data-commons (and some DICOM is in GC).

# Incorrect Behavior

The agent expects CDA to render or download the images.
