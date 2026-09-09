# ICDC query catalogue

ICDC exposes **125 root queries** at `https://caninecommons.cancer.gov/v1/graphql/` (POST only). The
complete, authoritative list (generated from live introspection) is
[../assets/query-fields.txt](../assets/query-fields.txt). This file curates the queries a researcher
actually needs, grouped into the three families, and flags the internal/empty ones to skip.

All queries return JSON `{"data": {...}}`; errors come back **HTTP 200** with an `errors` array.
Arguments are GraphQL named arguments inside the query — strings double-quoted, ints bare, list args
in `[...]`. Many queries also accept the generic `first` / `offset` / `orderBy` / `filter` arguments
(see [PAGINATION.md](PAGINATION.md)).

---

## 1. Portal faceted-search family (Elasticsearch-backed)

The cohort-building entry point. Defined verbatim in [../assets/search-schema.graphql](../assets/search-schema.graphql).
Full facet list and return shapes in [SEARCH.md](SEARCH.md).

| Query | Args | Returns | Use |
|---|---|---|---|
| `searchCases` | the 18 facet args + `search_text` | `SearchResult` | Repository + per-facet **counts** and the `caseIds`/`sampleIds`/`fileIds` for the current filter. The Explore-page engine. **Not paged; returns counts + ID arrays, not rows.** |
| `caseOverview` | facet args + `order_by`,`sort_direction`,`first`,`offset` | `[CaseOverviewES]` | Paged **case rows** for the facet filter. |
| `sampleOverview` | facet args (+`sample_ids`) + paging | `[SampleOverviewES]` | Paged **sample rows**. |
| `fileOverview` | facet args (+`file_level`,`sample_ids`,`file_uuids`) + paging | `[FileOverviewES]` | Paged **file rows**. |
| `globalSearch` | `input`, `first`, `offset` | `GlobalSearchResult` | Free-text across programs/studies/cases/samples/files/about-pages/model. |
| `createManifest` | `uuid: [String]` + paging | `String` (CSV) | Build a file-manifest CSV for the given file uuids → Cancer Genomics Cloud. See [FILES.md](FILES.md). |
| `externalDataOverview` | `clinical_study_designation` + paging | `[ExternalDataOverview]` | A study's links to other CRDC nodes / external image collections. |

> Portal `*Overview` and `globalSearch` default to **`first: 10`**.

## 2. Auto-generated node queries (one per data-model node)

Each node type is a root query taking **exact-match property args** (e.g. `study(clinical_study_designation: "OSA01")`)
**and** a `filter` object + `first`/`offset`/`orderBy`. They traverse relationships by nesting fields.
No default row limit — set `first` on large nodes. Per-node fields are in [ENTITIES.md](ENTITIES.md).

Populated, researcher-relevant nodes:
`program`, `study`, `study_arm`, `cohort`, `case`, `demographic`, `diagnosis`, `enrollment`,
`sample`, `file`, `visit`, `cycle`, `adverse_event`, `physical_exam`, `vital_signs`,
`disease_extent`, `prior_therapy`, `prior_surgery`, `canine_individual`, `registration`,
`study_site`, `principal_investigator`, `publication`, `human_relevance`, `biospecimen_source`,
`image_collection`.

Empty / placeholder nodes (querying them is valid but usually returns nothing — see SKILL.md critical
rule): `agent`, `agent_administration`, `follow_up`, `off_study`, `off_treatment`, `lab_exam`,
`image`, `assay`.

## 3. Cypher-backed convenience queries

Pre-joined combinations the portal uses; often the quickest path for a common task.

### Metrics & counts
- **Global (no args):** `numberOfPrograms`, `numberOfStudies` (Unrestricted only), `numberOfCases`,
  `numberOfSamples`, `numberOfFiles`, `numberOfStudyFiles`, `numberOfAliquots` (always 0),
  `volumeOfData` (bytes, Float), `schemaVersion`.
- **Parameterized:** `caseCountOfStudy(study_code)`, `sampleCountOfStudy`, `fileCountOfStudy`,
  `fileCountOfStudyFiles`, `caseCountOfProgram(program_id)`, `studyCountOfProgram`,
  `sampleCountOfProgram`, `fileCountOfProgram`, `studyFileCountOfProgram`,
  `sampleCountOfCase(case_id)`, `fileCountOfCase`, `studyFileCountOfCase`, `programCountOfStudy`,
  `programsCountOfCase`, `volumeOfDataOfStudy`/`OfProgram`/`OfCase`. (The `aliquot*Of*` variants exist
  but return 0.)
- `unifiedViewData(case_ids)` → `UnifiedCounts` — all metrics scoped to a case set (cart summary).

### Programs & studies
- `studiesByProgram` → `[StudyOfProgram]` — every study with program id, name, accession, per-study
  case/file/image/publication counts, CRDC links. The best "list everything" call.
- `studiesByProgramId(program_id)` → same, one program.
- `studyDetail(study_code)` → `[StudyDetail]` — a study's files (name/type/format/size/association).
- `studyStats` → `[StudyStat]` — per-study file count, total MB, case & sample counts.

### Cases & clinical summary
- `caseDetail(case_id)` → `CaseDetail` — one case's flattened program/study/arm/cohort + demographic
  + enrollment + primary diagnosis summary.
- `casesByStudyId(study_id)` → `[case]` — all cases of a study (`study_id` = `clinical_study_designation`).
- `casesInList(case_ids)` → `[CaseOverview]` — rich case overview for an explicit id list.
- `multiStudyCases(case_id)` → `MultiStudyCases` — the other cases/samples/files belonging to the same
  `canine_individual` (one dog across studies). See [multi_study_individual](../examples/multi_study_individual.md).

### Samples
- `samplesByCaseId(case_id)` → `[sample]`.
- `studySampleSiteCount` / `studySampleTypeCount` / `studySamplePathologyCount(study_codes)` →
  `[GroupCount]` — sample breakdowns for one or more studies.

### Files
- `filesOfCase(case_id)` / `filesOfCases(case_ids)` → `[FilesOfCase]`.
- `filesOfStudy(study_code)` → `[file]` (accepts `clinical_study_designation` **or** `accession_id`).
- `filesBySampleId(sample_id)` → `[file]`. `studyFiles(study_codes)` → `[file]` (study-level files).
- `fileDetail(file_ids)` → `[FileDetail]` — rich per-file record incl. `GUID` (DRS), `acl`,
  `file_location`, plus joined case/sample/diagnosis context.
- `fileInfo(file_ids)` → `[FileInfo]` — minimal DRS record: `GUID`, `md5`, `size`, `acl`, `url`.
- `filesInList(uuids)` / `filesInListDesc` → `[FileInList]` — cart table (sortable via `order_by`).
- `fileIdsFromFileName(file_name: [String])` → `[FileOverview]` — resolve uuids from file names.

### Per-study longitudinal clinical data → [CLINICAL.md](CLINICAL.md)
- `clinicalDataNodeNames`, `clinicalDataNodeCounts(study_code)`, `clinicalDataNodeCaseCounts(study_code)`.
- `visitNodeData`, `cycleNodeData`, `adverseEventNodeData`, `physicalExamNodeData`,
  `vitalSignsNodeData`, `diseaseExtentNodeData`, `priorTherapyNodeData`, `priorSurgeryNodeData`,
  `priorSurgeryNodeDataOverview` — each `(study_code)` → its clinical-event rows.
- `agentNodeData`, `agentAdministrationNodeData`, `followUpNodeData`, `offTreatmentNodeData`,
  `offStudyNodeData` exist but the underlying nodes are usually empty.
- `humanRelevanceNodeData(study_codes)` → `[HumanRelevanceNodeData]` — the human-cancer relevance
  statements that make ICDC a comparative-oncology resource.

## Internal / UI-plumbing queries (skip unless reverse-engineering the portal)

These are ES "type" objects exposed as root queries to back specific UI widgets; they take a property
arg per field and are not useful as data pulls: `breedCaseCount`, `cartChartData`, `cartChartItem`,
`cartOverview`, `cartOverviewData`, `caseOverview2`, `fileInList`, `fileOverview2`, `groupCount`,
`link`, `sampleOverview` (the property-arg variant — use the faceted one above), `studyOfProgram`,
`studyStat` (the property-arg variant — use `studyStats`), `unifiedCounts`.

## Resolving the schema at runtime

```graphql
{ __type(name: "case")   { fields { name } } }   # fields of a node
{ __type(name: "_caseFilter") { inputFields { name } } }   # filter operators for a node
{ __schema { queryType { fields { name } } } }   # all 125 query names
```
