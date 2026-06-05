# Discovering programs, projects & studies

PDC is small enough (~9 programs, ~30 projects, ~227 studies) to enumerate, but a disease or tissue
still spans several studies across programs and analytical fractions (a single cancer commonly has
separate Proteome and Phosphoproteome studies). When the user names a disease, tissue, gene, or
program rather than a `pdc_study_id`, **enumerate the matching studies first**, then run the real
per-study query over the set.

These enumeration queries are also how you avoid **guessing controlled-vocabulary filter values**.
`disease_type`, `experiment_type`, `analytical_fraction`, and `tissue_or_organ_of_origin` accept only
exact PDC enum strings, and a wrong value returns an **empty result with no `errors`** (not a 400). So
pull the valid values from the queries below (e.g. `diseasesAvailable` for `disease_type`,
`allExperimentTypes` for `experiment_type`) and pass one back verbatim — never a value you assumed.

## Repository-level overview

```graphql
{ getPDCMetrics { programs projects studies cases files data_size_TB } }   # live totals
{ dataStatsPerProgram { name project_count study_count data_file_count data_size_TB } }  # per program
{ allPrograms { name projects { name studies { pdc_study_id study_name analytical_fraction
    disease_types primary_sites experiment_type acquisition_type } } } }   # full hierarchy
```

`allPrograms` is the single fastest way to dump every study with its disease(s), site(s), fraction,
and experiment type — often enough to pick studies without any other call.

## By disease

```graphql
{ programsProjectsStudies(disease_type: "Lung Adenocarcinoma")
  { name projects { name studies { pdc_study_id study_name analytical_fraction experiment_type primary_sites } } } }
```

`programsProjectsStudies` also accepts `instrument_model`, `analytical_fraction`, and `experiment_type`
to narrow further. To see *what* disease values exist (and case counts):

```graphql
{ diseasesAvailable { disease_type project_submitter_id cases_count tissue_or_organ_of_origin } }
```

## By tissue / anatomical site

```graphql
{ tissueSitesAvailable { tissue_or_organ_of_origin project_submitter_id cases_count } }
```

`disease_type` (histology, e.g. *Clear Cell Renal Cell Carcinoma*) and `tissue_or_organ_of_origin` /
`primary_site` (anatomy, e.g. *Kidney*) are different axes — match the user's wording. `diseasesAvailable`
returns both, so it's a good bridge between them.

## By experiment / project

```graphql
{ allExperimentTypes(experiment_type: "Label Free") { experiment_type disease_type tissue_or_organ_of_origin } }
{ diseaseTypesPerProject { project_submitter_id analytical_fraction experiment_type cases { disease_type count } } }
{ program(program_submitter_id: "Clinical Proteomic Tumor Analysis Consortium")
  { name projects { project_submitter_id name studies { pdc_study_id study_name } } } }
```

## By gene / protein

A gene/protein isn't a study filter, but `geneSpectralCount(gene_name: …)` and `protein(protein: …)`
return `spectral_counts` tagged with `study_submitter_id` / `pdc_study_id`, telling you which studies
detected that gene/protein. See [QUANTITATION.md](QUANTITATION.md).

## By publication

```graphql
{ getPaginatedPublications(offset: 0 limit: 50)
  { total uiPublication { pubmed_id title year studies { pdc_study_id submitter_id_name } disease_types }
    pagination { total pages } } }
```

Accepts `disease_type`, `year`, `pubmed_id` to filter — a route from a known paper to its PDC studies.

## Then: resolve to the right study ID and version

Discovery queries return `pdc_study_id` (and sometimes `study_id`). Before a per-study query that
needs `study_id` (version-specific), confirm the latest version via `studyCatalog`. See
[ENTITIES.md](ENTITIES.md) and [examples/discover_studies_for_disease.md](../examples/discover_studies_for_disease.md).
