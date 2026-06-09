# Cross-repository search & linkage (the flagship use case)

CDA's whole reason to exist is connecting data **across** the CRDC repositories — GDC (genomics), PDC
(proteomics), IDC (imaging), GC (General Commons, formerly CDS), ICDC (canine). This is what the
single-commons skills can't do. Use CDA to answer "where does this data live?" and "which subjects/
files appear in more than one place?", then hand off.

## Three ways to see & filter by repository

### 1. The `<table>_data_at_<dc>` boolean columns — the reliable signal

Every table has `<table>_data_at_{gc,gdc,icdc,idc,pdc}` booleans and a `<table>_data_source_count`
integer (see [DATA-MODEL.md](DATA-MODEL.md)). Filter on them to express overlap precisely:

```python
# Subjects with data at BOTH GDC and PDC (verified live: 2,345 subjects, 275,617 related files)
summarize_subjects(match_all=['subject_data_at_gdc = true', 'subject_data_at_pdc = true'])

# Files present in more than one repository
get_file_data(match_all=['file_data_source_count > 1'])
```

### 2. `data_source=` — restrict to a repository

`summarize_subjects(data_source='GDC')` keeps subjects with GDC data. Its output also profiles the
**`data_source` Venn** of the result set.

### 3. The `data_source` Venn in `summarize_*` output

Every summary profiles `data_source` as **mutually-exclusive** repository combinations, e.g. (live):

```
data_source: { "gdc_exclusive": ..., "pdc_gdc_exclusive": 429,
               "idc_pdc_gdc_exclusive": 753, "pdc_exclusive": ..., ... }
```

i.e. how many entities are GDC-only vs exactly GDC+PDC vs exactly GDC+PDC+IDC, and so on. Because the
buckets are exclusive, "at GDC and also somewhere else" = (subjects with GDC) − (`gdc_exclusive`).
(Older docs render this as `GDC only`, `GDC + IDC`, `PDC + GDC + CDS + IDC`, where `CDS` is the old name
for GC.)

> **Avoid the `upstream_source` summary field for linkage.** Upstream flagged a known bug where it
> incorrectly links some records. Use the `data_at_<dc>` booleans / the `data_source` Venn for "which
> DC", and `upstream_identifiers.*` (the join table) for the actual per-repository ids.

## `upstream_identifiers` — the id crosswalk

To recover where a subject's data physically sits and under what ids, join the crosswalk:

```python
get_subject_data(
    match_from_file={'input_file': 'my_ids.tsv', 'input_column': 'subject',
                     'cda_column_to_match': 'subject_id'},
    add_columns='upstream_identifiers.*')
# -> upstream_source / upstream_field / upstream_id per subject (e.g. GC, GDC, PDC, IDC)
```

## Combining cohorts: `intersect_*`

When "A and B" can't be one filter — because A and B are two values of the *same* column, or live in
queries you ran separately — run each query and intersect the results (keep entities in **all**
inputs):

```python
ct  = get_subject_data(match_all=['anatomic_site = *kidney', 'file_type = CT Image Storage'])
mut = get_subject_data(match_all=['anatomic_site = *kidney', 'file_type = Annotated Somatic Mutation'])
both = intersect_subject_results(ct, mut)   # kidney subjects with BOTH an image and a mutation file
```

This is the cross-modal cohort pattern (imaging × sequencing, tumor × normal). Add
`add_columns='file.*', collate_results=True` and `expand_subject_results(both, 'file_data')` to see
which file is which. Worked: [../examples/intersect_cohorts.md](../examples/intersect_cohorts.md).

## Locate → hand off (CDA does not analyze or download)

CDA returns harmonized **metadata** and a `drs_uri` per file. It does not compute gene expression,
mutation frequency, or survival, and it does not fetch bytes. The intended flow:

1. **Locate** the cohort/files across repositories with CDA (this skill).
2. **For analysis**, hand the located study/project off to the specialized commons' skill:

   | Need | Skill |
   |---|---|
   | Gene-expression matrices, mutation frequency, survival, BAM slicing, CNV/SSM | `genomic-data-commons` |
   | Proteomics quantitation, PDC study tables | `proteomic-data-commons` |
   | DICOM imaging series / viewers | the imaging-data-commons |
   | General-Commons-only data | `general-commons` |

3. **To download**, take the `drs_uri` set (a manifest) to a cloud workspace — ISB-CGC, the Velsera
   Cancer Genomics Cloud, or Terra/FireCloud — and resolve the DRS objects there. Controlled-access
   files (`access = controlled`) still require the user's own dbGaP authorization in that workspace.
   See [../examples/files_and_drs.md](../examples/files_and_drs.md).

### The GDC handoff keys (verified)

CDA emits identifiers that resolve directly in the GDC API, so a located cohort crosses cleanly into
`genomic-data-commons`: a subject's `subject_id` is `PROGRAM.<gdc_submitter_id>` (e.g.
`CPTAC.C3L-03728` → GDC `cases.submitter_id = C3L-03728`), and a file's `file_id` is the GDC file UUID
(the part after `drs://dg.4dfc:`). The robust crosswalk in `cdapython` is
`add_columns='upstream_identifiers.*'`. Worked, tested handoffs (proteogenomics, BAM slicing, mutation
frequency): [../examples/handoff_to_gdc.md](../examples/handoff_to_gdc.md).

CDA's mutation table exists but is GDC-derived with unreliable counts — for rigorous somatic-mutation
analysis prefer `genomic-data-commons` ([DATA-MODEL.md](DATA-MODEL.md)).
