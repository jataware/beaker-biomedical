# Searching & filtering

CDA gives you three ways to narrow data, which combine freely on `summarize_*` and `get_*_data`.

## 1. Global keyword search (positional `search_terms`)

Bare strings search **every column** at once, case-insensitively; multiple terms are **AND**'d:

```python
summarize_subjects('kidney')             # anything tagged kidney
summarize_subjects('kidney', 'vcf')      # kidney AND vcf, anywhere
get_file_data('kidney', 'adeno*')        # wildcards allowed
```

Best for open-ended exploration ("what's in here about kidney?"). Once you know the column, switch to
explicit filters for precision.

## 2. Filter strings (`match_all` / `match_any`)

A filter string is `'COLUMN OP VALUE'`. **The spaces around `OP` are required** — `'sex = female'`
works, `'sex=female'` does not.

- **`match_all=[...]`** — every condition must hold (**AND**).
- **`match_any=[...]`** — at least one must hold (**OR**).
- Combine: `match_all` and `match_any` in the same call AND together (all of match_all, and at least
  one of match_any).

```python
summarize_subjects(match_all=['diagnosis = *adenocarcinoma*', 'species = human'])
summarize_files(match_all=['project_name = *cptac*'],
                match_any=['anatomic_site = *kidney*', 'anatomic_site = *bladder*'])
```

### Operators

| Operator | Works on | Notes |
|---|---|---|
| `=`  `!=` | numeric, boolean, string | string match is **case-insensitive** |
| `<`  `<=`  `>`  `>=` | numeric only | |

Chained numeric ranges are allowed in a single filter string:

```python
summarize_subjects(match_all=['70 < age_at_observation <= 80', 'species = human'])
```

### `NULL` — matching missing data

`NULL` is the special value for "no data". `'cause_of_death = NULL'` matches subjects missing a cause
of death; `'age_at_observation != NULL'` requires the field be present.

### Wildcards `*` — **a `cdapython` client feature**

In `cdapython`, `*` on either/both ends of a string VALUE enables partial matching:

```python
'diagnosis = *adenocarcinoma*'   # contains "adenocarcinoma" (any case, any surrounding words)
'anatomic_site = *kidney'        # ends with "kidney"
'sex = F*'                       # starts with F
```

> **The `*` wildcard is implemented in the client, not the service.** A raw REST `MATCH_ALL` does
> exact-match only (case-insensitive) and does **not** expand `*` (or SQL `%`). Verified against the
> live API: `diagnosis = *adenocarcinoma*` → **0** rows at REST, but `diagnosis = Adenocarcinoma` →
> 11,794. So for partial matches you must use `cdapython`; if you call REST directly, enumerate exact
> values with `column_values` first. See [REST-API.md](REST-API.md).

### Values are matched as stored — check casing first

Stored casing differs by column. Confirm with `column_values('col')` (which is case-insensitive)
before composing exact filters:

| column | stored as | example values |
|---|---|---|
| `sex` | lowercase | `female`, `male` |
| `species` | lowercase | `human`, `mouse`, `dog`, `human/mouse xenograft` |
| `format` | UPPERCASE | `BAM`, `BAI`, `VCF`, `BCR XML` |
| `diagnosis` | title-case | `Adenocarcinoma`, `Endometrioid adenocarcinoma` |
| `file_type` | title-case phrases | `CT Image Storage`, `Annotated Somatic Mutation` |

Exact string matching is case-insensitive (`'diagnosis = adenocarcinoma'` == `'... = Adenocarcinoma'`),
but **partial** matching needs the `*` wildcard, so spelling still matters: `'diagnosis =
*adenocarcinoma*'` catches `Endometrioid adenocarcinoma` too, whereas `'diagnosis = Adenocarcinoma'`
matches only the exact term.

## 3. Restrict by repository (`data_source`)

`data_source=` keeps only rows with data at the named upstream repository (`'GDC'`, `'IDC'`, `'PDC'`,
`'GC'`, `'ICDC'`; string or list):

```python
summarize_subjects(data_source='GDC')              # subjects with GDC data (+ cross-DC Venn in output)
get_file_data(match_all=['format = BAM'], data_source=['GDC', 'PDC'])
```

For *boolean* "has data at X" filters inside `match_all`, use the columns directly —
`'subject_data_at_pdc = true'` — which also lets you express overlap (`subject_data_at_gdc = true` AND
`subject_data_at_pdc = true`). See [CROSS-REPOSITORY.md](CROSS-REPOSITORY.md).

## 4. Match against a local file (`match_from_file`)

Restrict results to rows whose CDA column matches any value in a column of a local TSV — ideal when you
arrive with a list of IDs:

```python
get_subject_data(
    match_from_file={'input_file': 'mydatafile.tsv',
                     'input_column': 'subject',          # column in the TSV
                     'cda_column_to_match': 'subject_id'},# CDA column to match it against
    add_columns='upstream_identifiers.*')                # ...then see where their data lives
```

## Which column is on which table?

`sex`, `vital_status`, `diagnosis`, `age_at_observation`, `morphology`, `grade`, `stage`,
`observed_anatomic_site` are on **`observation`**; `anatomic_site`, `format`, `file_type`,
`tumor_vs_normal`, `access`, `drs_uri` on **`file`**; demographics (`species`, `race`, `year_of_birth`)
on **`subject`**; `project_name` on **`project`**. You can still filter on any of them from a `subject`
or `file` query — CDA joins under the hood — but knowing the home table explains the count semantics
(see [DATA-MODEL.md](DATA-MODEL.md)). Don't know the column? `columns(description='...')` —
[DISCOVERY.md](DISCOVERY.md).
