# Discovering programs & studies (and deciding GC is the right commons)

GC is small enough to enumerate (~9 programs, ~89 studies). When the user names a program, disease, or
topic rather than a `phs_accession`, list the matching studies first, then run the per-study queries.
**While you're here, sanity-check that GC is even the right commons** (see the last section).

## Repository overview

```graphql
{ programsCount studiesCount version { data_version datetime description } }   # live totals + release
{ programList { acronym name num_studies } }                                  # programs at a glance
```

`programList` (a UI helper) currently returns programs like: **MP2PRT** (Molecular Profiling to Predict
Response to Treatment), **CPTAC**, **CCDI** (Childhood Cancer Data Initiative), **TCIA-RADIOLOGY** (TCIA
Radiology Collections), **PDXNet**, **HTAN** (Human Tumor Atlas Network), **DCCPS** (Division of Cancer
Control and Population Sciences), **NCIcaNano** (NCI Alliance for Nanotechnology), **Kids First**.
Treat counts/names as illustrative — call it live for the current set.

## List & filter studies

`studies` is the workhorse and the only query that searches by name/acronym:

```graphql
{ studies(first: 100) { phs_accession study_name study_acronym study_data_types study_access
    number_of_participants number_of_samples } }                 # browse everything
{ studies(study_acronyms: ["KF-ESGR"]) { phs_accession study_name } }
{ studies(study_names: ["CPTAC Pan-Cancer"]) { phs_accession study_acronym study_data_types } }
{ studies(phs_accessions: ["phs001287","phs001228"]) { phs_accession study_name } }
```

`study_data_types` (e.g. `["Genomics", "Proteomics"]`) and `study_access` (Open/Controlled) are the
fields that tell you what a study actually holds. The `studies` query has **no disease/tissue filter
argument** — to find studies by disease, the best path is the **faceted search**:
`searchSubjects(primary_diagnoses: ["..."]) { subjectCountByPhsAccession { group subjects } }` returns
the studies (by `phs_accession`) that contain that diagnosis and how many subjects each has, in one
call (see [SEARCH.md](SEARCH.md)). Discover the valid `primary_diagnoses` values from
`searchSubjects { subjectCountByPrimaryDiagnosis { group subjects } }`. Alternatives:
`globalSearch(input: "...")`, or scanning `studies` + `study_description`.

## Programs

```graphql
{ programs(first: 50) { program_name program_acronym program_short_name institution } }
{ programs(program_names: ["Childhood Cancer Data Initiative"]) { program_acronym program_external_url } }
```

## Free-text search — `globalSearch`

The fastest "does GC have anything on X?" check. It's a UI/transform query (not a Data Type Query) and
returns hits bucketed by entity with counts:

```graphql
{ globalSearch(input: "Ewing sarcoma" first: 20 offset: 0)
  { study_count studies { phs_accession }
    subject_count sample_count file_count program_count
    about_count about_page { /* portal copy */ } } }
```

Use it to locate candidate studies, then resolve `phs_accession` and switch to the Data Type Queries.

## Is GC even the right commons? (decide before going deep)

GC is **data-type agnostic and largely mirrors data submitted to specialized commons**, so a hit here
often is *also* (and better) served elsewhere. After discovery, look at `study_data_types`:

- Pure **Genomics** study (mutations/expression/BAMs) → redirect to **`genomic-data-commons`**.
- Pure **Proteomics** study (mass-spec quantitation) → redirect to **`proteomic-data-commons`**.
- **Imaging** pixels → the **imaging-data-commons**.
- Only stay in GC when the data type is GC-specific (e.g. **NCIcaNano** nanomaterial
  `characterizations`/`compositions`, certain **CCDI/DCCPS/PDXNet** studies), the user explicitly wants
  General Commons / CDS / CGC, or the specialized commons doesn't have it.

This matches the skill's mandate: **for ambiguous requests prefer the more specific commons; fall back
to GC only when warranted.**
