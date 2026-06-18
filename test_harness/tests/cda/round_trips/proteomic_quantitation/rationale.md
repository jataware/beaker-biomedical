# Intended Behavior

The prompt names a concrete, PDC-resident cohort: the CPTAC-3 lung adenocarcinoma patients. The agent confirms this cohort has proteomics in CDA — its mass-spec files are `format = mzML` (all PDC) and/or the subjects carry `data_source = PDC` — and collects the PDC-resident subjects and files. Because CDA is metadata-only and holds no abundance values, protein quantitation hands off to `proteomic-data-commons` (GraphQL at `proteomic.datacommons.cancer.gov/graphql`): discover the study, then build a per-study log-ratio quant matrix, yielding a tumor-vs-normal protein matrix CDA cannot produce.

Relevant CDA queries:
- `summarize_subjects(match_all=['project_short_name = CPTAC-3', 'primary_site = lung', 'diagnosis = Adenocarcinoma'], data_source='PDC')` confirms the cohort.
- `summarize_files(match_all=['format = mzML'])` confirms the mass-spec proteomics files (all PDC).
- The `file` table exposes `tumor_vs_normal` (Tumor / Normal), so matched tumor/normal proteomics files exist for this design.

# Incorrect Behavior

The agent routes protein abundance to GDC, or claims CDA returns quantitation values.

# Live verification (2026-06-18)

- CPTAC-3 lung adenocarcinoma PDC subjects = **225**
  `summarize_subjects(match_all=['project_short_name = CPTAC-3', 'primary_site = lung', 'diagnosis = Adenocarcinoma'], data_source='PDC', return_data_as='dataframe_list')[0]['number_of_matching_subjects']`
- mzML files total = **46,792**, ALL at PDC (GDC/IDC/GC/ICDC = 0)
  `summarize_files(match_all=['format = mzML'], data_source='PDC', return_data_as='dataframe_list')[0]['number_of_matching_files']`
- mzML files by tumor_vs_normal: Tumor = 39,179; Normal = 27,488 (matched tumor/normal proteomics exist)
  `summarize_files(match_all=['format = mzML', 'tumor_vs_normal = Tumor'])` / `... = Normal`
- The `file` table carries NO abundance/quantitation column (cols: file_id, access, anatomic_site, category, drs_uri, file_description, file_name, file_type, format, size, tumor_vs_normal, data_source).
- No `number` is graded: the prompt asks "how do I get there?" (a workflow), not for a count, so a count is not naturally elicited. Method/routing and the false-capability trap are all left to the two `behavior` checks; no `must_not_contain`, since a correct answer that negates the wrong path ("not GDC", "CDA returns no quant") would false-fail a substring guard.
- Mechanics note: `project_short_name` / `primary_site` / `diagnosis` are SUBJECT-level filters; they return 0 if applied to a file query. The cohort is established via the subject query; the mzML files are queried at file level.
