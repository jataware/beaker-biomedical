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

## Which repositories hold a cohort? (the `data_at_*` booleans)

```python
# Subjects with data at BOTH GDC and PDC (verified live: 2,345 subjects; 275,617 related files)
summarize_subjects(match_all=['subject_data_at_gdc = true', 'subject_data_at_pdc = true'])

# Restrict to one repository and read the Venn of everything those subjects also touch:
summarize_subjects(data_source='GDC')
#   data_source breakdown -> GDC only, GDC + IDC, PDC + GDC + IDC, ...  (exclusive buckets)

# Files that live in more than one repository:
get_file_data(match_all=['file_data_source_count > 1'])
```

Prefer these `<table>_data_at_<dc>` booleans / the `data_source` Venn over the `upstream_source` field
(known linking bug).

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
- `project` is the only table without a `_data_at_gc` boolean (GC isn't tracked at project level).
- Numbers move between releases — re-run and cite `release_metadata`.
