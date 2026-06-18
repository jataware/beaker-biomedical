# Intended Behavior

The prompt names a real, locatable cohort: the TCGA-LUAD tumor BAMs. As of 2026-06-18, `summarize_files(match_all=['format = BAM', 'project_short_name = TCGA-LUAD', 'tumor_vs_normal = tumor'], data_source='GDC')` returns 3486 matching files, and every one is `access = controlled` (0 are `open`). So the agent can find the file set in CDA, but cannot fulfill the byte-level request.

CDA neither moves nor processes bytes — it returns `drs_uri` and `access` only. The agent locates the files in CDA, then hands off: bytes are resolved in a cloud workspace (ISB-CGC, Velsera CGC, or Terra; controlled data like these BAMs needs dbGaP authorization), and somatic variant calling is a pipeline run in that workspace or a GDC-served product.

# Incorrect Behavior

The agent writes a `cdapython` download or slice call, or claims CDA runs pipelines / calls variants.

# Verified numbers (2026-06-18)

- TCGA-LUAD, `format = BAM`: 5053 files.
  `summarize_files(match_all=['format = BAM', 'project_short_name = TCGA-LUAD'], data_source='GDC', return_data_as='dataframe_list')[0]` → number_of_matching_files = 5053
- TCGA-LUAD tumor BAMs: 3486 files.
  `summarize_files(match_all=['format = BAM', 'project_short_name = TCGA-LUAD', 'tumor_vs_normal = tumor'], data_source='GDC', return_data_as='dataframe_list')[0]` → number_of_matching_files = 3486
- All 3486 are controlled access (`access = controlled` → 3486; `access = open` → 0).
