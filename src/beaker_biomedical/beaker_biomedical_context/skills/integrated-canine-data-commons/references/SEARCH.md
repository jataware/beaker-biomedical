# Faceted search & cohort building

The Elasticsearch-backed portal queries are the entry point for "find me cases/samples/files matching
these criteria." They share one filter vocabulary. Defined verbatim in
[../assets/search-schema.graphql](../assets/search-schema.graphql).

## The facet arguments (shared by `searchCases`, `caseOverview`, `sampleOverview`, `fileOverview`)

Every facet arg is a **list of strings** (`[String]`, default `[]` = no constraint). Multiple values
within one facet are OR'd; different facets are AND'd. The 18 dimensions:

| Group | Facet args |
|---|---|
| Study | `program`, `study`, `study_type`, `biobank`, `study_participation` |
| Case / clinical | `breed`, `diagnosis`, `disease_site`, `stage_of_disease`, `response_to_treatment`, `sex`, `neutered_status` |
| Sample | `sample_site`, `sample_type`, `sample_pathology` |
| File | `file_association`, `file_type`, `file_format` |

Plus: `searchCases` takes `search_text: String`; `caseOverview`/`sampleOverview`/`fileOverview` take
`order_by`, `sort_direction` (`ASC`/`DESC`), `first` (default 10), `offset` (default 0);
`fileOverview` additionally takes `file_level`, `case_ids`, `sample_ids`, `file_uuids`;
`sampleOverview` takes `sample_ids`; all take `case_ids`.

**Values are controlled vocabularies.** Get them from `searchCases` facet counts — never hardcode a
guess. Sample live values:
- `study_type`: `Clinical Trial` (452), `Genomics` (344), `Transcriptomics/Genomics` (117),
  `Transcriptomics` (87), `Genomics/Transcriptomics` (29).
- `study_participation`: `Single Study` (1011), `Multiple Study` (18).
- `breed`: `Mixed Breed` (221), `Labrador Retriever` (104), `Golden Retriever` (88),
  `Rottweiler` (51), `Boxer` (45), `Greyhound` (40), … plus `Unknown` / `Other`.

## `searchCases` → SearchResult (counts + IDs, NOT rows, NOT paged)

Returns three things; pick what you need:

1. **Repository counts for the current filter:** `numberOfPrograms`, `numberOfStudies`,
   `numberOfCases`, `numberOfSamples`, `numberOfFiles`, `numberOfStudyFiles`, `numberOfAliquots`
   (0), `volumeOfData`.
2. **The matching IDs (full arrays, unpaged):** `caseIds`, `sampleIds`, `fileIds`, `studyFileIds`.
   Feed these into `caseOverview`/`sampleOverview`/`fileOverview` (via `case_ids`/`sample_ids`/
   `file_uuids`) or `casesInList`/`filesOfCases`/`createManifest` to get rows or a manifest.
3. **Per-facet group counts** — two parallel families:
   - `caseCountBy<Facet>` — counts over the **whole repository** (the unfiltered facet landscape):
     `caseCountByProgram`, `caseCountByStudyCode`, `caseCountByStudyType`, `caseCountByBiobank`,
     `caseCountByStudyParticipation`, `caseCountByBreed`, `caseCountByDiagnosis`,
     `caseCountByDiseaseSite`, `caseCountByStageOfDisease`, `caseCountByGender`,
     `caseCountByNeuteredStatus`, `caseCountByFileFormat`, plus `programsAndStudies`.
   - `filterCaseCountBy<Facet>` — counts **after applying the current filter** (what the portal shows
     to refine a selection): `filterCaseCountByProgram`, `…ByBreed`, `…ByDiagnosis`, `…BySex`,
     `…BySampleSite`, `…BySampleType`, `…BySamplePathology`, `…ByFileAssociation`, `…ByFileType`,
     `…ByFileFormat`, `…ByResponseToTreatment`, `…ByStageOfDisease`, etc.

   Each is `[{ group: String, count: Int }]`. Use `caseCountBy*` to discover the landscape; use
   `filterCaseCountBy*` to see what's left after narrowing.

```graphql
{ searchCases(diagnosis: ["Osteosarcoma"], sex: ["Male"]) {
    numberOfCases numberOfSamples numberOfFiles
    caseIds
    filterCaseCountByBreed { group count }
    filterCaseCountByStudyCode { group count } } }
```

## Row queries (`caseOverview` / `sampleOverview` / `fileOverview`)

Same facet args, but paged and returning flat rows (the `*ES` types — `CaseOverviewES`,
`SampleOverviewES`, `FileOverviewES`). **Default `first: 10`** — set it and loop `offset` for the
full set (see [PAGINATION.md](PAGINATION.md)). `CaseOverviewES` carries `case_id`, `study_code`,
`study_type`, `breed`, `diagnosis`, `stage_of_disease`, `age`, `sex`, `neutered_status`, `weight`,
`disease_site`, `individual_id`, `files`, `other_cases`, and the diagnosis detail fields.

```graphql
{ caseOverview(diagnosis: ["Osteosarcoma"], first: 50, offset: 0,
               order_by: "case_id", sort_direction: "ASC") {
    case_id study_code breed sex age disease_site stage_of_disease } }
```

## `globalSearch` → GlobalSearchResult (free text)

`globalSearch(input: "osteosarcoma", first: 10, offset: 0)` searches everything and returns typed,
counted buckets: `program_count`+`programs`, `study_count`+`studies`, `case_count`+`cases`,
`sample_count`+`samples`, `file_count`+`files`, `about_count`+`about_page`, `model_count`+`model`
(data-dictionary matches). Each bucket has its own lightweight fields (e.g. `cases { case_id
disease_term breed }`, `studies { clinical_study_designation clinical_study_name }`). Good first move
when the user's term could be a disease, study, breed, or model property. `first`/`offset` page within
each bucket.

## Picking the right tool

- "How many cases of X / what breeds/studies have X?" → `searchCases` facet counts.
- "List the cases/samples/files matching X" → `caseOverview`/`sampleOverview`/`fileOverview` (page it).
- "I have a term but don't know what it is" → `globalSearch`.
- "Exact graph traversal / a field not in the `*ES` row" → node queries ([ENTITIES.md](ENTITIES.md)).
