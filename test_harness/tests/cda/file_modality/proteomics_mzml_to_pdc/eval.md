# Expect

- **Expect:** `column_values('format')` → `mzML`; `summarize_files(match_all=['format = mzML'])` →
  **≈ 46,792 files, all PDC**; CDA returns `drs_uri` only — quantitation is a **`proteomic-data-commons`**
  job, not GDC.

# Failure Cases

- **Fail signs:** routes proteomics to GDC; claims CDA computes abundances.

# Automated Checks

```yaml
checks:
  - number:
      name: "mzml_files"
      target: 46792
      tolerance_percent: 15
  - substring_any: ["proteomic-data-commons", "PDC"]
  - behavior: "counted files via summarize_files(format = mzML) and routed quantitation to PDC; noted CDA returns drs_uri only (no abundances)"
  - must_not_contain: ["quantitation in GDC", "run the analysis in GDC", "CDA computes", "CDA returns abundances"]
```
