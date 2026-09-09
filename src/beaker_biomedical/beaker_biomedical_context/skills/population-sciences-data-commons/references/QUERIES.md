# PS-DC query catalogue

Single endpoint: `POST https://populationsciences.datacommons.cancer.gov/v1/graphql/` with body
`{"query": "...", "variables": {}}` — **the `variables` key is required** (even empty), and **GET is
rejected**. HTTP 200 even on errors — inspect `errors`. The full introspected list (74 fields) is
[../assets/query-fields.txt](../assets/query-fields.txt); every object type's fields are in
[../assets/schema-types.txt](../assets/schema-types.txt). Both are generated from live introspection
(no upstream repo exists).

> **Prototype caveat:** classifications below are from live probing (~June 2026). The "currently
> erroring" queries fail with `Unable to connect to localhost:7687` (Neo4j down), not a query bug —
> they may come online later. Re-probe before relying on them.

---

## ✅ Working — study-level (Elasticsearch-backed)

These are the queries to use. Details + return-type fields in [STUDIES.md](STUDIES.md) and
[SEARCH.md](SEARCH.md).

| Query | Args | Returns | Use |
|---|---|---|---|
| `globalStatsBar` | — | `[GlobalStatsBar]` | One card per study: `study_short_name`, `number_of_participants`, `study_design`, `study_type`, `cancer_type_count`, `data_volume`. The quickest overview. |
| `tabStudy` | study-property filters + paging | `[TabStudy]` | The rich study table: name/id/description, design, enrollment & study years, `biospecimen_collection`, `data_collection_category`, `study_status`, `dbgap_accession_id`, counts, demographics, `study_country`, primary diagnosis sites, personnel/publications. |
| `studyDemographics` | `study_short_name`, `race`, `ethnicity`, `sex`, age args + paging | `[StudyDemographics]` | Per-study demographics incl. `participant_sexes`/`participant_races`/`participant_ethnicities` (each `[GroupCounts]`), `participant_median_age`, `participant_age_range`, `participant_count_by_age`. |
| `primarySiteMorphology` | `study_short_name`, sort + paging | `[PrimarySiteMorphology]` | Per-study cancer `cancer_diagnosis_primary_site_collection` and `cancer_diagnosis_disease_morphology_collection`. |
| `dataCollectionPage` | `study_short_name` | `[data_collection_page]` | Per-study `data_collection` categories (questionnaire/exposure domains). |
| `studyGeneral` | `study_short_name` | `[StudyGeneral]` | Per-study `personnel`, `publication`, `data_file`, `associated_links`, `primary_diagnosis_disease_count`. |
| `studyFiles` | `study_short_name`, `data_file_*`, `association`, sort + paging | `[StudyFiles]` | Study-level files: `data_file_name/type/format/size`, `data_file_uuid`, **`drs_uri`**, `data_file_access_control`, `data_file_signed_url`. See [STUDIES.md](STUDIES.md). |
| `searchStudies` | the study facet args | `SearchResult` | Faceted study search — counts + `studyCountBy*` facets. See [SEARCH.md](SEARCH.md). |
| `minMaxBoundQuery` | — | `[minMaxBoundQuery]` | Slider bounds: participant-count & age & year lower/upper bounds across studies. |

## ❌ Currently erroring — Neo4j backend unreachable

Defined in the schema but return `Unable to connect to localhost:7687` on the deployed prototype. **Do
not present these as usable**; mention they exist and may come online, and retry.

- **Repository totals / search-from-lists:** `schemaVersion`, `nodeCounts`, `nodeCountsFromLists`,
  `findIdsFromLists`, `idsLists`, `groupCount`, `groupList`, `armInfo`, `programArms`,
  `armsByProgramsFromLists`.
- **Subject (participant) facets & lists** — the breast-cancer-template families:
  `subjectList`, and `subjectListBy{Program,Study,Diagnoses,RecurrenceScore,TumorSize,TumorGrade,
  ErStatus,PrStatus,ChemotherapyRegimen,EndocrineTherapy,MenopauseStatus,TissueType,TissueComposition,
  FileAssociation,FileType}`; the parallel `subjectCountBy{…}FromLists`; `subjectInfo`.
- **File-record level:** `fileOverview`, `fileInfo`, `filesInList`.
- **Auto-generated node queries** (each takes the standard Bento `<prop>` / `<prop>_in` /
  `<prop>_contains` / … filter args): `aliquot`, `analyte`, `cross_reference_database`,
  `demographic_data`, `diagnosis`, `exposure`, `family_medical_history`, `file`, `follow_up`,
  `fraction`, `institution`, `laboratory_procedure`, `program`, `project`, `report`, `sample`,
  `stratification_factor`, `study`, `study_subject`, `therapeutic_procedure`.

> These node names reveal the intended data model (program → project → study → study_subject →
> diagnosis / sample → aliquot/analyte/fraction; plus exposure, family_medical_history, follow_up,
> laboratory_procedure, therapeutic_procedure, report). Useful as a roadmap once the backend is live.

## Counts use `subjects`

Both `GroupCount` and `GroupCounts` are `{ group: String, subjects: Int }`. In the study-level facets
(`studyCountByStudyDesign`, etc.) `subjects` is the **number of studies** in that group, not people.

## Introspecting (remember the `variables` key)

```json
{"query": "{ __type(name: \"TabStudy\") { fields { name } } }", "variables": {}}
{"query": "{ __schema { queryType { fields { name } } } }", "variables": {}}
```
