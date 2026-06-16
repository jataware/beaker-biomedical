# Expect

- **CDA locate:** confirm the cohort has proteomics — `summarize_files(match_all=['format = mzML'])`
  (≈46,792 PDC files) or `subject_data_at_pdc = true`; collect the PDC-resident subjects/files.
- **↳ Hand-off:** CDA is metadata-only and has **no abundance values**; protein quantitation is a PDC
  job → **`proteomic-data-commons`** (GraphQL at `proteomic.datacommons.cancer.gov/graphql`).
- **PDC analyze:** that skill's `examples/discover_studies_for_disease.md` (find the study via
  `studyCatalog`/`programsProjectsStudies`) then `examples/quant_matrix.md` (log-ratio quant matrix per
  study). Result = a tumor-vs-normal protein quant matrix CDA cannot produce.

# Failure Cases

- **Fail signs:** routes protein abundance to GDC; claims CDA returns quant values.

# Automated Checks

```yaml
checks:
  - behavior: "confirmed the PDC-resident cohort in CDA (format = mzML / subject_data_at_pdc), then handed off to proteomic-data-commons for the quantitation"
  - substring_any: ["proteomic-data-commons", "PDC"]
  - substring_any: ["metadata-only", "no abundance", "CDA cannot produce", "CDA has no abundance"]
  - must_not_contain: ["protein abundance from GDC", "GDC for protein abundance", "CDA returns quant"]
```
