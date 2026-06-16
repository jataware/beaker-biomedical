# Expect

- **Expect:** `summarize_files(match_all=['format = DICOM'])` → **≈ 1,080,056 files**, split
  **≈ 994,073 IDC + ≈ 85,983 GC** (good answers notice it isn't *only* IDC); analysis/viewing →
  the imaging-data-commons.

# Failure Cases

- **Fail signs:** asserts all DICOM is IDC; counts subjects instead of files.

# Automated Checks

```yaml
checks:
  - number:
      name: "dicom_files"
      target: 1080056
      tolerance_percent: 15
  - number:
      name: "idc_dicom"
      target: 994073
      tolerance_percent: 15
  - number:
      name: "gc_dicom"
      target: 85983
      tolerance_percent: 20
  - substring_all: ["IDC", "GC"]
  - behavior: "summarized files (not subjects) and reported the DICOM split across IDC + GC"
  - must_not_contain: ["all DICOM is IDC", "only IDC", "exclusively IDC", "all DICOM images are in IDC"]
```
