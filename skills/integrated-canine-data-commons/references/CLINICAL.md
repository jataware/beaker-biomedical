# Longitudinal clinical-trial data (per study)

Clinical-trial studies (`clinical_study_type: "Clinical Trial"`, e.g. the `COTC*` studies) carry
longitudinal event data — visits, treatment cycles, adverse events, exams, lesion measurements, prior
treatment. ICDC exposes these as a family of **`*NodeData(study_code)`** convenience queries (one per
clinical node), plus counts. Genomics/transcriptomics-only studies generally have none of this.

This data lives on the clinical-event nodes hanging off `case` → `visit`/`cycle`/`enrollment` (see the
graph in [ENTITIES.md](ENTITIES.md)). The `*NodeData` queries pre-join the path from study to event so
you don't have to traverse it yourself; each returns a flat list scoped to one study.

## Discover what a study has first

```graphql
{ clinicalDataNodeNames                                   # which clinical node types exist at all
  countsRecords: clinicalDataNodeCounts(study_code: "COTC022") {       # # of records per node
    cycle visit adverse_event physical_exam vital_signs disease_extent
    prior_therapy prior_surgery follow_up off_treatment off_study agent agent_administration lab_exam }
  countsCases: clinicalDataNodeCaseCounts(study_code: "COTC022") {     # # of distinct cases per node
    cycle visit adverse_event physical_exam vital_signs disease_extent prior_therapy prior_surgery } }
```

A node with count 0 means that study didn't collect it (or the node is one of the globally-empty ones
— `agent`, `agent_administration`, `follow_up`, `off_study`, `off_treatment`, `lab_exam`).

## The per-node data queries — each `(study_code: String!)`

| Query | Returns rows of | Key fields (besides `case_id`) |
|---|---|---|
| `visitNodeData` | visits | `visit_date`, `visit_number`, `visit_id` |
| `cycleNodeData` | treatment cycles | `cycle_number`, `date_of_cycle_start`, `date_of_cycle_end` |
| `adverseEventNodeData` | adverse events | `adverse_event_term`, `adverse_event_grade`(+description), `date_of_onset`, `date_of_resolution`, `ongoing_adverse_event`, `dose_limiting_toxicity`, `attribution_to_*`, `adverse_event_agent_name/dose` |
| `physicalExamNodeData` | physical exams | `date_of_examination`, `body_system`, `pe_finding`, `pe_comment`, `day_in_cycle`, `assessment_timepoint` |
| `vitalSignsNodeData` | vital signs | `date_of_vital_signs`, `time_of_observation`, `body_temperature`, `pulse`, `respiration_pattern`, `modified_ecog`, `body_surface_area`, `patient_weight` (most numeric values come with split `_unit`/`_original` fields) |
| `diseaseExtentNodeData` | lesion/RECIST-style assessments | `lesion_number`, `lesion_site`, `lesion_description`, `measurable_lesion`, `target_lesion`, `longest_measurement`, `date_of_evaluation`, `measured_how`, `evaluation_number`, `evaluation_code` |
| `priorTherapyNodeData` | pre-enrollment therapy | `agent_name`, `prior_therapy_type`, `dose_schedule`, `total_dose`, `best_response_to_prior_therapy`, NSAID/steroid exposure fields, `date_of_first/last_dose` |
| `priorSurgeryNodeData` | pre-enrollment surgery | `date_of_surgery`, `procedure`, `anatomical_site_of_surgery`, `surgical_finding`, `residual_disease`, `therapeutic_indicator` |
| `priorSurgeryNodeDataOverview` | summary object | aggregated prior-surgery overview |
| `agentNodeData`, `agentAdministrationNodeData`, `followUpNodeData`, `offTreatmentNodeData`, `offStudyNodeData` | — | usually empty (placeholder/deprecated nodes) |

```graphql
{ adverseEventNodeData(study_code: "PRECINCT01") {
    case_id adverse_event_term adverse_event_grade date_of_onset
    dose_limiting_toxicity ongoing_adverse_event } }
```

> The `*NodeData` **return types are a curated subset** of the underlying node and don't always match
> the node's property names (e.g. `VitalSignsNodeData` splits each measurement into `_unit`/`_original`
> fields and omits some; `respiration_rate` the value isn't exposed). Introspect the return type if a
> field errors: `{ __type(name:"VitalSignsNodeData"){ fields { name } } }`.

These queries accept `first`/`offset`/`orderBy`/`filter` too — but they're already study-scoped, so
the row counts are usually small. For analysis, pull the table for the study, then join to
demographics/diagnosis via `case_id` (e.g. `caseDetail(case_id)` or the `demographic`/`diagnosis` node
queries). See [../examples/clinical_node_data.md](../examples/clinical_node_data.md).

## Comparative-oncology context: `humanRelevanceNodeData`

`humanRelevanceNodeData(study_codes: [String])` returns each study's `human_relevance_statement`,
`relevant_human_cancer`, `relevant_human_genes`, `relevant_human_pathways`,
`relevant_experimental_therapeutic_intervention`, and `nci_link_to_relevant_human_cancer` — i.e. *why*
the canine study is a model for a specific human cancer. This is the field set that distinguishes ICDC
from a purely veterinary dataset; surface it when a user asks how a canine study maps to human disease.
