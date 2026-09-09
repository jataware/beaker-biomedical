# Cross-repository search & linkage (the flagship use case)

CDA's whole reason to exist is connecting data **across** the CRDC repositories — GDC (genomics), PDC
(proteomics), IDC (imaging), GC (General Commons, formerly CDS), ICDC (canine). This is what the
single-commons skills can't do. Use CDA to answer "where does this data live?" and "which subjects/
files appear in more than one place?", then hand off.

## Ways to see & filter by repository

> **The mechanism differs between cdapython and REST — get this right.** In **cdapython 2.1.0** the
> `<table>_data_at_<dc>` booleans and `<table>_data_source_count` are **not searchable** (filtering on
> them raises *"not a searchable CDA column"*); use the **`data_source=` argument** instead. In the raw
> **REST** API those boolean columns **are** valid in `MATCH_ALL`. Both routes give identical counts.

### 1. `data_source=` — the cdapython way (single repo, or a list for AND)

`data_source=` is how cdapython expresses repository membership. A **single** value keeps entities at
that repo; a **list ANDs** them — kept only if present at *every* listed repo (intersection):

```python
summarize_subjects(data_source='GDC')                     # subjects with GDC data (verified: 50,213)
summarize_subjects(data_source='PDC')                     # subjects with PDC data (verified: 5,755)
# Subjects with data at BOTH GDC and PDC — the overlap (verified live: 2,345 subjects):
summarize_subjects(data_source=['GDC', 'PDC'])
get_subject_data(data_source=['GDC', 'PDC'])              # the 2,345 rows; each has a `data_source` list col
```

Per-source sizes and key overlaps (verified live, March 2026): GDC 50,213 · IDC **79,649** (largest) ·
GC 70,862 · PDC 5,755 · ICDC 1,029. **IDC × GDC = 15,699** subjects with both imaging and sequencing
(the flagship imaging × sequencing cohort). GC ∩ GDC = 5,937. **ICDC overlaps only IDC** —
`data_source=['ICDC','IDC']` → 80; `['ICDC','GDC']` and `['ICDC','PDC']` → 0.

### 1b. The boolean columns — the REST way (equivalent, REST only)

```python
# REST MATCH_ALL accepts the booleans (cdapython does not). Verified: 2,345 subjects, 275,617 files.
import requests
requests.post("https://cda.datacommons.cancer.gov/summary/subject",
              json={"MATCH_ALL": ["subject_data_at_gdc = true", "subject_data_at_pdc = true"]}
             ).json()["result"][0]   # -> total_count 2345, file_count 275617
```

> **Overlap is a *subject* concept — files are single-homed.** Each file physically lives in exactly one
> repository, so `file_data_source_count > 1` returns **0** and `data_source=['GDC','PDC']` on files
> returns 0. To find files for a *cross-repository cohort*, scope the subjects first (above), then pull
> their files.

### 2. The per-row `data_source` column (cdapython results)

cdapython result rows carry a single **`data_source`** column whose value is the **list** of repos
holding that entity — e.g. `['GDC','PDC']`, `['GC','GDC','IDC','PDC']`. (The individual `data_at_*`
booleans are not returned.) Inspect or group on it to profile a fetched cohort:

```python
df = get_subject_data(data_source=['GDC', 'PDC'])
df['data_source'].astype(str).value_counts()    # how the overlap splits, e.g. ['GDC','PDC']: 429, ...
```

### 3. The `data_source` Venn in `summarize_*` output

Every summary profiles `data_source` as **mutually-exclusive** repository combinations. **The key
format differs by interface** (both seen live):

- **cdapython** (`return_data_as='dict'`): human-readable keys —
  `{'GDC only': 7924, 'PDC and GDC': 170, 'IDC and GDC': 2027, 'PDC and IDC and GDC': 161,
    'PDC and GC and IDC and GDC': 247, ...}`
- **REST** (raw JSON): `*_exclusive` keys —
  `{'gdc_exclusive': 7924, 'gdc_pdc_exclusive': 170, 'gdc_idc_exclusive': 2027,
    'gdc_pdc_idc_exclusive': 161, 'gdc_gc_pdc_idc_exclusive': 247, ...}`

Either way the buckets are exclusive: "at GDC and also somewhere else" = (subjects with GDC) − (GDC
only). (`CDS` in very old output is the former name for `GC`.) `summarize_subjects` dict output also
includes a `subject_data_source_count_summary`.

> **Match venn keys by set membership, not the literal string** — the token order inside a key is not
> guaranteed (live keys read `GDC and PDC` / `IDC and GDC and PDC`, not `PDC and GDC` / `PDC and IDC and
> GDC`), and the counts drift each release. The numbers above are illustrative; recompute live and parse
> the keys by which repos they contain.

> **Avoid the `upstream_source` summary field for linkage.** Upstream flagged a known bug where it
> incorrectly links some records. Use `data_source=` / the `data_source` Venn for "which DC", and
> `upstream_identifiers.*` (the join table) for the actual per-repository ids.

## `upstream_identifiers` — the id crosswalk

To recover where a subject's data physically sits and under what ids, join the crosswalk:

```python
get_subject_data(
    match_from_file={'input_file': 'my_ids.tsv', 'input_column': 'subject',
                     'cda_column_to_match': 'subject_id'},
    add_columns='upstream_identifiers.*', collate_results=True)   # collate is REQUIRED here
# -> nested `upstream_identifiers_data` frame: aligned (upstream_source, upstream_field, upstream_id) rows
#    e.g. for CPTAC.C3L-03728: GDC case.submitter_id=C3L-03728, case.case_id=4447a969-...
```

> **⚠️ Pass `collate_results=True` for this join.** Without it, `upstream_source`, `upstream_field`, and
> `upstream_id` come back as three **independently-sorted, different-length lists** (verified: source
> len 4, id len 7 for one subject) — zipping them positionally pairs the wrong (source, id) values (it
> will hand you a GDC source next to a GC dbGaP id). Only `collate_results=True` gives correctly aligned
> rows. The `PROGRAM.<submitter_id>` shortcut in [../examples/handoff_to_gdc.md](../examples/handoff_to_gdc.md)
> is the quick path; this collated crosswalk is the robust one.

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
