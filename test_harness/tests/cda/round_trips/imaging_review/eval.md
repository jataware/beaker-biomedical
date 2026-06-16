# Expect

- **CDA locate:** `get_file_data(match_all=['format = DICOM'], data_source='IDC')` → file rows with
  `drs_uri` (≈994k DICOM at IDC).
- **↳ Hand-off:** CDA returns `drs_uri`, never pixels; series/viewers live at the imaging-data-commons
  (and some DICOM is in GC).

# Failure Cases

- **Fail signs:** expects CDA to render or download images.

# Automated Checks

```yaml
checks:
  - behavior: "located DICOM files in CDA (returning drs_uri), then routed series/viewing to the imaging-data-commons"
  - substring_any: ["imaging-data-commons", "IDC", "viewer"]
  - substring_any: ["drs_uri", "DRS"]
  - must_not_contain: ["CDA renders", "CDA displays", "download the images from CDA", "view the pixels in CDA"]
```
