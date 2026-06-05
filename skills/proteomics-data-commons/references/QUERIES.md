# PDC query catalogue (all 40 queries)

Single endpoint: `POST https://proteomic.datacommons.cancer.gov/graphql` with body
`{"query": "{ queryName(args) { fields } }"}`. PDC returns HTTP 200 even on query errors — inspect the
`errors` array. Arguments are GraphQL named args (strings double-quoted, ints bare).

**"Extra accepted args"** below come from the upstream Swagger docs: many queries accept more filter
arguments than their canonical signature shows. **Required args** must be present (especially
`offset`/`limit` on paginated queries). Study-ID choice and versioning: see [ENTITIES.md](ENTITIES.md).

---

## Metrics & discovery

### `getPDCMetrics`
No args. Repository-wide totals.
`{ getPDCMetrics { programs projects studies cases files data_size_TB } }`

### `dataStatsPerProgram`
No args. Per-program counts.
Fields: `program_id program_submitter_id name project_count study_count data_file_count data_size_TB`

### `diseasesAvailable`
Accepts `disease_type`, `tissue_or_organ_of_origin`, `project_submitter_id`, `project_id` (all optional filters).
Fields: `disease_type project_id project_submitter_id cases_count tissue_or_organ_of_origin`

### `tissueSitesAvailable`
Accepts `tissue_or_organ_of_origin`, `project_submitter_id`, `project_id`.
Fields: `tissue_or_organ_of_origin project_id project_submitter_id cases_count`

### `diseaseTypesPerProject`
Accepts `project_submitter_id`, `project_id`.
Fields: `project_id project_submitter_id experiment_type analytical_fraction cases { disease_type count }`

### `allExperimentTypes`
Required `experiment_type` (e.g. `Label Free`); also accepts `tissue_or_organ_of_origin`, `disease_type`.
Fields: `experiment_type tissue_or_organ_of_origin disease_type`

### `getPaginatedPublications`
Required `offset`, `limit`; also accepts `disease_type`, `year`, `pubmed_id`.
Fields: `total uiPublication { publication_id pubmed_id doi author title journal journal_url year abstract citation studies { pdc_study_id submitter_id_name } disease_types } pagination { count sort from page total pages size }`

---

## Program / project

### `allPrograms`
No args. Full program → project → study hierarchy.
`{ allPrograms { program_id program_submitter_id name projects { project_id project_submitter_id name studies { pdc_study_id study_submitter_id study_name analytical_fraction disease_types primary_sites experiment_type acquisition_type } } } }`

### `program`
Required `program_submitter_id` (or `program_id`). One program + its projects + studies.
Fields: `program_id program_submitter_id name projects { project_id project_submitter_id name studies { ... } }`

### `programsProjectsStudies`
Required `disease_type`; also accepts `instrument_model`, `analytical_fraction`, `experiment_type`.
Returns the program→project→study hierarchy filtered to studies matching the disease. The main
"which studies have this disease?" query.

---

## Study

### `study`
Required `pdc_study_id` (also accepts `study_id`, `study_submitter_id`). Study details + counts.
Fields: `study_id pdc_study_id study_submitter_id program_id project_id study_name study_description program_name project_name disease_type primary_site analytical_fraction experiment_type cases_count aliquots_count filesCount { data_category file_type files_count }`

### `studyCatalog`
Optional `pdc_study_id`. Version catalog (omit the arg for all studies).
Fields: `pdc_study_id versions { study_id study_submitter_id submitter_id_name study_shortname study_version is_latest_version }`

### `studyExperimentalDesign`
Required `pdc_study_id`. Per-run plex layout: which aliquot occupies each label channel
(`label_free`, `itraq_113…121`, `tmt_126…135n`).
Key fields: `study_run_metadata_id analyte acquisition_type experiment_type plex_dataset_name number_of_fractions` plus a block per channel `{ aliquot_id aliquot_run_metadata_id aliquot_submitter_id }`.

### `experimentalMetadata`
Required `study_submitter_id`. Run/protocol/file metadata per study run.
Fields: `experiment_type analytical_fraction study_run_metadata { study_run_metadata_id fraction protocol { protocol_id instrument } aliquot_run_metadata { aliquot_id aliquot_submitter_id label experiment_number fraction replicate_number analyte } files { file_type data_category file_location } }`

### `protocolPerStudy`
Required `study_submitter_id`. Wet-lab + MS protocol (~60 fields).
Highlights: `quantitation_strategy experiment_type labeled_quantitation isobaric_labeling_reagent enrichment_strategy digestion_reagent instrument_make instrument_model dissociation_type ms1_resolution ms2_resolution dda_topn normalized_collision_energy acquistion_type analytical_technique` (full list in [assets/spec.json](../assets/spec.json)).

### `workflowMetadata`
Accepts `workflow_metadata_id`, `workflow_metadata_submitter_id`, `study_submitter_id`, `pdc_study_id`, `study_id`.
CDAP bioinformatics workflow provenance: `refseq_database_version uniport_database_version hgnc_version raw_data_processing sequence_database_search phosphosite_localization ms1_data_analysis psm_report_generation cdap_reports` etc.

### `filesCountPerStudy`
Required `pdc_study_id`; also accepts `study_id`, `study_submitter_id`, `file_type`, `data_category`.
Fields: `study_id pdc_study_id study_submitter_id file_type files_count data_category`

---

## Case / clinical / biospecimen

See [CLINICAL.md](CLINICAL.md) for how the clinical entity is split across these queries.

### `allCases`
No required args (query bakes in `offset:0 limit:10`). Lightweight case list.
Fields: `case_id case_submitter_id project_id project_submitter_id disease_type primary_site externalReferences { ... }`

### `case`
Required `case_submitter_id` (also accepts `case_id`, `pdc_study_id`, `study_id`). The **deep**
single-case query: `demographics`, `samples` (→ `aliquots` → `aliquot_run_metadata`), full
`diagnoses` (100+ fields), `exposures`, `follow_ups`, `treatments`. Use POST — the field set is huge.

### `getPaginatedCases`
Required `offset`, `limit`. Paginated case list.
Fields: `total cases { case_submitter_id project_id project_submitter_id disease_type } pagination { ... }`

### `paginatedCasesSamplesAliquots`
Required `pdc_study_id`, `offset`, `limit` (accepts other study/program IDs).
case → sample → aliquot → aliquot_run_metadata for a study. The query for mapping aliquots to cases.

### `clinicalPerStudy`
Required `pdc_study_id`. All clinical for a study's cases in one shot — demographic + diagnosis fields
plus nested `exposures`, `follow_ups`, `treatments`, `samples`. Not paginated; use POST.

### `clinicalMetadata`
Required `study_id`. Aliquot-level clinical summary.
Fields: `aliquot_id aliquot_submitter_id morphology primary_diagnosis tumor_grade tumor_stage tumor_largest_dimension_diameter`

### `paginatedCaseDemographicsPerStudy`
Required `study_id`, `offset`, `limit`.
Fields: `total caseDemographicsPerStudy { case_id case_submitter_id disease_type primary_site demographics { ethnicity gender race vital_status age_at_index ... } } pagination { ... }`

### `paginatedCaseDiagnosesPerStudy`
Required `study_id`, `offset`, `limit`.
Fields: `total caseDiagnosesPerStudy { case_submitter_id disease_type primary_site diagnoses { primary_diagnosis tumor_grade tumor_stage ajcc_pathologic_stage morphology ... } } pagination { ... }`

### `paginatedCaseExposuresPerStudy`
Required `study_submitter_id`, `offset`, `limit`. Tobacco/alcohol/environmental exposure fields.

### `paginatedCaseFollowUpsPerStudy`
Required `pdc_study_id`, `offset`, `limit`. Longitudinal follow-up fields (disease response, ECOG, recurrence …).

### `paginatedCaseTreatmentsPerStudy`
Required `pdc_study_id`, `offset`, `limit`. Therapy fields (agents, dose, intent, outcome …).

### `biospecimenPerStudy`
Required `pdc_study_id` (accepts `study_id`, `study_submitter_id`). Flat aliquot↔sample↔case rows
with statuses.
Fields: `aliquot_id sample_id case_id aliquot_submitter_id sample_submitter_id case_submitter_id aliquot_status case_status sample_status project_name sample_type disease_type primary_site pool taxon externalReferences { ... }`

---

## Files

See [FILES.md](FILES.md) for downloads, signed URLs, expiry, and rate limits.

### `fileMetadata`
Required `offset`, `limit` (**limit ≤ 25000**); also accepts `file_id`, `file_name`, `file_submitter_id`, `data_category`, `file_type`, `file_format`.
Rich per-file metadata + `aliquots { aliquot_id aliquot_submitter_id sample_id case_id case_submitter_id }`.

### `filesPerStudy`
Required `study_id`, `offset`, `limit`; also accepts `study_submitter_id`, `pdc_study_id`, `file_name`, `file_type`, `data_category`, `file_format`.
**Only query that exposes `signedUrl { url }`** (the downloadable S3 link). Can be slow on large studies.

### `getPaginatedFiles`
Required `study_id`, `offset`, `limit`; same extra filters as `filesPerStudy`. Paginated file list
**without** signed URLs (use `filesPerStudy` when you need to download).

---

## Gene / protein / quantitation

See [QUANTITATION.md](QUANTITATION.md) for the matrix shape, `data_type` values, and spectral-count caveats.

### `getPaginatedGenes`
Required `gene_name` (matches multiple genes, e.g. `TP53` → `TP53`, `TP53AIP1`, …); query bakes in `offset`/`limit`.
Fields: `total genesProper { gene_id gene_name NCBI_gene_id authority description organism chromosome locus proteins assays } pagination { ... }`

### `geneSpectralCount`
Required `gene_name`. Gene record + `spectral_counts { project_submitter_id plex spectral_count distinct_peptide unshared_peptide study_submitter_id }` across studies. First call may be slow (then cached).

### `aliquotSpectralCount`
Required `gene_name`, `dataset_alias` (e.g. `FFPE_Discovery_Phospho_TMT_Gr12`). Per-aliquot spectral counts for one gene in one dataset.

### `paginatedSpectralCountPerStudyAliquot`
Required `study_id`, `plex_name`, `gene_name`, `offset`, `limit`.
Fields: `total spectralCounts { study_id study_submitter_id pdc_study_id plex spectral_count distinct_peptide unshared_peptide } pagination { ... }`

### `protein`
Required `protein` (UniProt or RefSeq accession, e.g. `M0R009`). Resolves the protein to its gene and
returns that gene's spectral counts across projects.

### `quantDataMatrix`
Required `pdc_study_id`, `data_type`. Returns the **entire** quantitation matrix as a 2-D array under
`data` — no pagination. First row is the header `["Gene/Aliquot", "<aliquot_id>:<aliquot_submitter_id>", …]`;
each subsequent row is `[gene_name, value, value, …]`. `data_type` is `log2_ratio` or
`unshared_log2_ratio` (other workflow-dependent types exist; an unavailable type returns
`"Matrix data not found!"`). **Note the unusual syntax**: the matrix itself takes no GraphQL subfield
selection — `{ quantDataMatrix(pdc_study_id: "PDC000127" data_type: "log2_ratio") }`.

---

## Entity references

### `reference`
Required `entity_type`, `entity_id`; optional `reference_type`. One entity's references.
Fields: `reference_id entity_type entity_id reference_type reference_entity_type reference_entity_alias reference_resource_name reference_resource_shortname reference_entity_location`

### `pdcEntityReference`
Required `entity_type` (`study`/`case`/…), `entity_id` (UUID of that type), `reference_type` (`internal`/`external`). Same field set as `reference`.
