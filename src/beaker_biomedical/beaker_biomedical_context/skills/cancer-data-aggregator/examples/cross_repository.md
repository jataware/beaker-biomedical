# Cross-repository: compile a program & find where data lives

CDA's signature move — pull a program together no matter which commons it landed in, and see which
repositories hold a cohort. Background: [../references/CROSS-REPOSITORY.md](../references/CROSS-REPOSITORY.md).

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")
```

## Compile CPTAC across all commons

CPTAC data is spread across GDC (genomics), PDC (proteomics), and IDC (imaging). One query gathers it
regardless of source:

```python
columns(column=['*project*'])                    # -> project_name has the definition we want
summarize_subjects(match_all='project_name = *cptac*')   # ~3000+ subjects across DCs
summarize_files(match_all='project_name = *cptac*')      # where the files are, by type/source

# Narrow to the modalities/sites of interest, then fetch file rows (with drs_uri) to build a manifest:
get_file_data(match_all='project_name = *cptac*',
              match_any=['anatomic_site = *kidney*', 'anatomic_site = *bladder*'])
```

The `summarize_*` output includes a `data_source` Venn showing how those subjects/files split across
GDC / PDC / IDC (and overlaps). Hand the `drs_uri`s to a cloud workspace to actually retrieve files
([files_and_drs.md](files_and_drs.md)).

## Which repositories hold a cohort? (the `data_source=` argument)

In cdapython, filter repository membership with **`data_source=`** — a single value for one repo, or a
**list to AND** (entities present at *all* listed repos). The `<table>_data_at_<dc>` booleans are
**not searchable in cdapython** (they work only in raw REST `MATCH_ALL`; see
[rest_api.md](rest_api.md)).

```python
# Subjects with data at BOTH GDC and PDC (verified live: 2,345 subjects; 275,617 related files)
summarize_subjects(data_source=['GDC', 'PDC'])     # list = AND/intersection

# Restrict to one repository and read the Venn of everything those subjects also touch:
summarize_subjects(data_source='GDC')
#   data_source breakdown -> 'GDC only', 'IDC and GDC', 'PDC and IDC and GDC', ...  (exclusive buckets)

# Overlap is a SUBJECT concept: files are single-homed, so file_data_source_count > 1 is always 0.
# To get files for a cross-repo cohort, scope subjects first, then pull their files.
```

Prefer `data_source=` / the `data_source` Venn over the `upstream_source` field (known linking bug).

## "I have a list of IDs — where else does their data live?" (`match_from_file`)

Start from a local TSV of subject IDs (e.g. a cohort you got from IDC) and discover their footprint
across CDA:

```python
# mydatafile.tsv has a column named `subject`
get_subject_data(
    match_from_file={'input_file': 'mydatafile.tsv', 'input_column': 'subject',
                     'cda_column_to_match': 'subject_id'},
    add_columns='upstream_identifiers.*')        # upstream_source / _field / _id per subject

summarize_files(match_from_file={'input_file': 'mydatafile.tsv', 'input_column': 'subject',
                                 'cda_column_to_match': 'subject_id'})   # files available, by source
```

## Then hand off

CDA has *located* the data and given you `drs_uri`s. For analysis, route to the specialized commons'
skill (gene expression / mutation frequency / survival → `genomic-data-commons`; proteomics quant →
`proteomic-data-commons`; DICOM imaging → the imaging-data-commons; GC-only → `general-commons`). CDA
itself does no analysis and no downloads.

## Notes

- `data_source` valid values: `'GDC'`, `'IDC'`, `'PDC'`, `'GC'`, `'ICDC'`. GC was formerly **CDS**;
  older output may print `CDS`.
- **GC** (70,862 subjects) is multimodal, not clinical-only: 478,638 GC-resident files spanning genomics
  (FASTQ/CRAM/BAM/VCF/MAF) and imaging (DICOM, MR/CT), mostly `access=controlled`. Top GC programs by
  subject are DCCPS prostate/CRC CIDR studies and CCDI childhood-cancer, plus re-hosted TCGA/CPTAC/HTAN
  slices.
- **ICDC** (1,029) is the canine commons: `species=dog` ⇔ ICDC exactly; all 2,895 files are `access=open`
  and keyed by `category` (`file_type` is always null for ICDC). There is **no `breed` column** in CDA.
- **Gotcha:** `column_values(col, data_source='IDC')` can **time out server-side (>300 s)** for
  high-cardinality columns (`anatomic_site`, `tumor_vs_normal`) — cdapython surfaces it as a misleading
  `JSONDecodeError: Expecting value`. Use `summarize_files(data_source='IDC')[...]` for those
  breakdowns, or filter the cohort first (`match_all=['anatomic_site = *kidney', ...]`), which works.
- `project` is the only joinable-entity table without a `_data_at_gc` *boolean* — but GC projects exist
  (77 `GC.*` project_ids; project rows carry data_source `GC`). It's a missing boolean, not missing data.
- Numbers move between releases — re-run and cite `release_metadata`.
