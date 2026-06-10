# Files, DRS URIs, and the cloud handoff (why there's no direct download)

CDA finds files and returns their metadata — including a **`drs_uri`** and an **`access`** flag — but it
**does not download data**. There is no `download()` and no signed HTTP URL in the API. You assemble the
file set here, then resolve the DRS objects in a cloud workspace. Background:
[../references/DATA-MODEL.md](../references/DATA-MODEL.md) and [../auth.yaml](../auth.yaml).

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")
```

## List files and collect their DRS URIs

```python
files = get_file_data(match_all=['project_name = *cptac*', 'format = BAM'])
files[['file_id', 'file_name', 'drs_uri', 'access', 'size', 'data_source']].head()
# drs_uri is a GA4GH DRS identifier (e.g. drs://...), NOT a direct download link.
# `data_source` is the per-row repository list (files are single-homed, so it's a 1-element list, e.g. ['GDC']).
```

Size the set and check open vs controlled before committing to a pull:

```python
summarize_files(match_all=['project_name = *cptac*', 'format = BAM'])   # counts, sizes, by source
column_values('access')        # -> open, controlled

# Save the manifest (the drs_uri + ids ARE your manifest) for the cloud step:
get_file_data(match_all=['project_name = *cptac*', 'format = BAM'],
              return_data_as='tsv', output_file='cptac_bams_manifest.tsv')
```

## Resolve the data in a cloud workspace

```python
# There is no CDA download call. To get bytes:
#   1. The drs_uri + metadata rows above are your manifest.
#   2. Load it into a cloud workspace that resolves CRDC DRS objects:
#        - ISB Cancer Gateway in the Cloud (ISB-CGC)
#        - Velsera Cancer Genomics Cloud (CGC)
#        - Terra / FireCloud
#   3. For files where access == "controlled", the user needs their own dbGaP authorization for the
#      underlying study; CDA never holds or checks credentials.
print("Resolve drs_uri values in ISB-CGC / Velsera CGC / Terra — not via CDA. See ../auth.yaml")
```

## Need analysis, not just files?

CDA locates; it doesn't analyze. Once you've identified the study/project/files, hand off to the
specialized commons' skill:

- gene-expression matrices, mutation frequency, survival, BAM slicing, CNV/SSM → **`genomic-data-commons`**
- proteomics quantitation, PDC study tables → **`proteomic-data-commons`**
- DICOM imaging series / viewers → the **imaging-data-commons**
- General-Commons-only data → **`general-commons`**

Those skills can take a GDC/PDC file id or project and do the downstream work (and, for GDC,
controlled-access download via its own token flow).

## Notes

- **`size` is in bytes** (a `bigint`); sum it to estimate egress/storage before resolving a manifest.
- **`access`** is `open` or `controlled`; searching metadata never needs auth, only resolving
  controlled bytes does (dbGaP, in the cloud workspace).
- The per-row **`data_source`** column tells you which repository each file physically lives in (a
  1-element list, since files are single-homed) — useful for choosing the right cloud resource. (The
  `file_data_at_<dc>` booleans exist only in the REST catalogue, not in cdapython results.)
- CDA's `drs_uri` may be empty for some records; fall back to `file_id` / `file_crdc_id` +
  `upstream_identifiers.*` to chase the file in its home repository.
- **IDC (imaging) files differ from GDC.** An IDC file's `drs_uri` is a **comma-separated list** of many
  `drs://dg.4dfc:<uuid>` objects (one CDA "file" = one DICOM series = ~hundreds of instances; verified:
  174 URIs in one CT row) — split on `,` before resolving, unlike a GDC BAM whose `drs_uri` is a single
  URI equal to `file_id`. IDC is **100% `open` / `format = DICOM`** (994,073 files, all open), so imaging
  needs no dbGaP step — whereas GDC is majority `controlled`. ICDC files are also all `open`.
