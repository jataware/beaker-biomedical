# PDC data model & identifiers

PDC organizes everything under a fixed hierarchy. Knowing it tells you which query to call and how
the IDs chain together.

```
program  ──<  project  ──<  study  ──<  case  ──<  sample  ──<  aliquot  ──<  aliquot_run_metadata
                                 │                                                (one labeled channel
                                 ├──< file                                         in a TMT/iTRAQ plex)
                                 └──< protocol / experimental design / workflow metadata

gene / protein  ──<  spectral_counts (span many studies)   ──<  quantitation matrix (per study)
```

- A **program** (e.g. *Clinical Proteomic Tumor Analysis Consortium*) contains **projects** (e.g.
  *CPTAC-2*, *CPTAC3 Discovery and Confirmatory*), which contain **studies**.
- A **study** is one analyte × experiment (e.g. *CPTAC CCRCC Discovery Study - Proteome*). It has an
  analytical fraction (Proteome, Phosphoproteome, …) and an experiment type (TMT10, iTRAQ4, Label
  Free, …). Quantitation matrices, files, protocol, and experimental design are all per-study.
- A **case** is a patient/donor. A case has **samples** (biospecimens); each sample has **aliquots**;
  each aliquot maps to **aliquot_run_metadata** — the specific labeled channel (e.g. `tmt_126`) in a
  plex. This chain is how a quantitation column resolves back to a patient.

## The three study identifiers (the #1 source of confusion)

| ID | Form | Example | Stable across versions? |
|---|---|---|---|
| `pdc_study_id` | Human-readable accession | `PDC000127` | **Yes** — prefer this |
| `study_id` | UUID | `dbe94609-1fb3-11e9-b7f8-0a80fada099c` | **No** — version-specific |
| `study_submitter_id` | Long descriptive name | `CPTAC CCRCC Discovery Study - Proteome S044-1` | Mostly, but verbose/ambiguous |

**Why it matters:** each study can have multiple **versions** (created when underlying data changes
substantially). `pdc_study_id` stays the same across versions; `study_id` is a *different UUID per
version*. So a hard-coded `study_id` can silently resolve to a stale release.

**Resolve IDs with `studyCatalog`** (lists every `pdc_study_id` and its versions with
`is_latest_version`) or **`study`** (returns all three IDs plus counts):

```graphql
{ studyCatalog(pdc_study_id: "PDC000127") {
    pdc_study_id
    versions { study_id study_submitter_id submitter_id_name study_version is_latest_version } } }
```

```graphql
{ study(pdc_study_id: "PDC000127") {
    pdc_study_id study_id study_submitter_id study_name disease_type analytical_fraction
    experiment_type cases_count aliquots_count } }
```

### Which ID does each per-study query want?

Most per-study queries *accept* any of the three as a named argument (verified live: `study` works
with `study_submitter_id` even though its signature shows `pdc_study_id`). But each documents one
canonical arg, and it pays to use the documented one:

| Canonical arg = `pdc_study_id` | Canonical arg = `study_id` | Canonical arg = `study_submitter_id` |
|---|---|---|
| `study`, `studyCatalog`, `studyExperimentalDesign`, `filesCountPerStudy`, `clinicalPerStudy`, `paginatedCaseFollowUpsPerStudy`, `paginatedCaseTreatmentsPerStudy`, `paginatedCasesSamplesAliquots`, `biospecimenPerStudy` | `filesPerStudy`, `getPaginatedFiles`, `clinicalMetadata`, `paginatedCaseDemographicsPerStudy`, `paginatedCaseDiagnosesPerStudy` | `experimentalMetadata`, `protocolPerStudy`, `paginatedCaseExposuresPerStudy` |

When a query wants `study_id` (version-specific), get the **latest** version's UUID from
`studyCatalog` first. Full per-query argument lists are in [QUERIES.md](QUERIES.md).

## Other identifiers

| Entity | Stable ID | Submitter ID | Notes |
|---|---|---|---|
| program | `program_id` (UUID) | `program_submitter_id` (name) | `program` query takes the submitter id |
| project | `project_id` (UUID) | `project_submitter_id` (e.g. `CPTAC-2`) | |
| case | `case_id` (UUID) | `case_submitter_id` (e.g. `C3N-00386`) | `case` query takes `case_submitter_id` |
| sample | `sample_id` (UUID) | `sample_submitter_id` | also carries `gdc_sample_id` for GDC cross-linking |
| aliquot | `aliquot_id` (UUID) | `aliquot_submitter_id` (e.g. `CPT0026410003`) | quant-matrix columns are `aliquot_id:aliquot_submitter_id` |
| file | `file_id` (UUID) | `file_submitter_id` | |
| gene | `gene_id` (UUID) | `gene_name` (HGNC symbol) | plus `NCBI_gene_id` |

**Cross-commons linking:** PDC samples carry `gdc_sample_id` / `gdc_project_id`, and `externalReferences`
on cases/biospecimens point to GDC, IDC, and other CRDC resources. Use these to join PDC proteomics to
GDC genomics for the same cases.

## Entity reference queries

`reference` and `pdcEntityReference` resolve external/internal references for an entity:

```graphql
{ pdcEntityReference(entity_type: "study", entity_id: "dbe94609-1fb3-11e9-b7f8-0a80fada099c", reference_type: "external")
  { reference_id reference_resource_name reference_resource_shortname reference_entity_location } }
```

`entity_type` is e.g. `study`, `case`, `diagnosis`; `entity_id` must be the UUID of an object of that
type; `reference_type` is `internal` or `external`.
