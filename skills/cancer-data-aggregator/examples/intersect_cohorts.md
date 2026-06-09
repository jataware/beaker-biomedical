# Cross-modal cohorts with intersect / collate / expand

Some cohorts can't be one filter — when the two conditions are different values of the **same** column
(a *tumor* BAM and a *normal* BAM), or different file types for the same subjects. Run each query, then
**intersect** the results to keep entities present in both. Background:
[../references/CROSS-REPOSITORY.md](../references/CROSS-REPOSITORY.md) and
[../references/FUNCTIONS.md](../references/FUNCTIONS.md).

```python
from cdapython import *
set_api_url("https://cda.datacommons.cancer.gov/")
```

## Matched tumor + normal BAMs

```python
column_values('format')           # confirm: BAM is stored UPPERCASE
column_values('tumor_vs_normal')  # tumor / normal

normal = get_subject_data(match_all=['tumor_vs_normal = normal', 'format = BAM'])
tumor  = get_subject_data(match_all=['tumor_vs_normal = tumor',  'format = BAM'])

both = intersect_subject_results(normal, tumor)   # subjects with BOTH a tumor and a normal BAM
both.to_csv('bams_tumor_normal.csv')

# Keep filtering by ANDing more conditions into each query before intersecting:
n_lung = get_subject_data(match_all=['tumor_vs_normal = normal', 'format = BAM', 'anatomic_site = lung'])
t_lung = get_subject_data(match_all=['tumor_vs_normal = tumor',  'format = BAM', 'anatomic_site = lung'])
both_lung = intersect_subject_results(n_lung, t_lung)
```

## Imaging × sequencing: CT images + somatic-mutation files for the same kidney patients

When you also need to know *which* file is which, add the file columns, **collate**, then **expand**:

```python
column_values('file_type')        # -> "CT Image Storage", "Annotated Somatic Mutation", ...

ct  = get_subject_data(match_all=['anatomic_site = *kidney', 'file_type = CT Image Storage'],
                       add_columns='file.*', collate_results=True)
mut = get_subject_data(match_all=['anatomic_site = *kidney', 'file_type = Annotated Somatic Mutation'],
                       add_columns='file.*', collate_results=True)

both = intersect_subject_results(ct, mut)        # kidney subjects with BOTH an image and a mutation file
expand_subject_results(both, 'file_data')        # one row per file: drs_uri/file_id/access aligned
```

Why collate + expand: `add_columns='file.*'` without `collate_results=True` fans each subject out into
one row per file and you can't tell which `file_id` is the CT vs the mutation file. `collate_results`
bundles the joined file rows into a nested `file_data` column; `expand_subject_results(df, 'file_data')`
then lays them out one-per-row with values aligned. (`add_columns='observation.*'` collates into
`observation_data`; the pattern is `<table>_data`.)

## How intersect works

- `intersect_subject_results(*dfs)` / `intersect_file_results(*dfs)` keep only entities (by
  `subject_id` / `file_id`) present in **all** input frames, merging their columns.
- If two inputs carry added columns from different upstream queries that won't reconcile, pass
  `ignore_added_columns=True` to merge just the base subject/file columns.
- It's an AND. For OR, put the alternatives in one query's `match_any` instead.

## Notes

- Confirm value casing first (`format` UPPERCASE, `sex` lowercase, `file_type` title-case phrases);
  wildcards (`*kidney`) need `cdapython`, not raw REST.
- This locates and assembles the cohort + its `drs_uri`s — resolve/download in a cloud workspace
  ([files_and_drs.md](files_and_drs.md)); analyze in the relevant specialized commons.
