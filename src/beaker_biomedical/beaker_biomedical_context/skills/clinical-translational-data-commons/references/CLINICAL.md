# Per-study clinical & clinical-trial data

Two queries return a study's full longitudinal records, grouped by node type and pre-counted:
`clinicalData` (observational/clinical nodes) and `clinicalTrialData` (treatment nodes). Both take
`(study_short_name: String)` (or `study_id`) and return one object per study. They're the structured
counterpart to the faceted search — use them to pull every diagnosis/treatment/specimen record for a
study, then join on `participant_ids`.

## `clinicalData(study_short_name)` → ClinicalData

Each node type comes with its data list **plus two counts** (`<node>NodeCount` = records,
`<node>ParticipantCount` = distinct participants). `unique_node_types` tells you which nodes the study
actually has.

| Field | Node data type | Key fields (besides `participant_ids`) |
|---|---|---|
| `diagnosisNodeData` (+`diagnosisNodeCount`,`diagnosisParticipantCount`) | `ClinicalDiagnosis` | `ctep_disease_term`, `primary_diagnosis_disease_group`, `primary_disease_site`, `histology`, `histological_subtype`, `snomed_disease_term`/`_code`, `meddra_disease_code`, `date_of_diagnosis` |
| `demographicNodeData` | `ClinicalDemographic` | `sex`, `race`, `ethnicity`, `age_at_enrollment`, `height`, `weight`, `body_surface_area`, `occupation`, `income`, `highest_level_of_education` |
| `exposureNodeData` | `ClinicalExposure` | `carcinogen_exposure` |
| `specimenNodeData` | `ClinicalSpecimen` | `specimen_category`, `specimen_type_concept_code`, `anatomical_collection_site`, `tissue_category`, `assessment_timepoint`, `collection_date` |
| `participantStatusNodeData` | `ClinicalParticipantStatus` | `survival_status`, `off_study`, `off_study_reason` |

```graphql
{ clinicalData(study_short_name: "CMB") {
    unique_node_types
    diagnosisNodeCount diagnosisParticipantCount
    diagnosisNodeData { participant_ids ctep_disease_term primary_disease_site histology } } }
# CMB: unique_node_types = [diagnosis, demographic, exposure, specimen, participant_status]
#      diagnosisNodeCount 249, demographicNodeCount 248, exposureNodeCount 248,
#      specimenNodeCount 1140, participantStatusNodeCount 124
```

## `clinicalTrialData(study_short_name)` → ClinicalTrialData

The treatment side, same `<node>NodeData` / `<node>NodeCount` / `<node>ParticipantCount` shape:

| Field | Node data type | Key fields |
|---|---|---|
| `targetedTherapyNodeData` | `ClinicalTargetedTherapy` | `targeted_therapy`, `targeted_therapy_dose`, `targeted_therapy_frequency` |
| `nonTargetedTherapyNodeData` | `ClinicalNonTargetedTherapy` | `non_targeted_therapy`, `*_dose`, `*_frequency`, `best_response_to_non_targeted_therapy` |
| `radiotherapyNodeData` | `ClinicalRadiotherapy` | `radiological_procedure`, `radiological_procedure_anatomical_location`, `radiation_dose`, `radiation_extent`, `radiation_frequency` |
| `surgeryNodeData` | `ClinicalSurgery` | `surgical_procedure`, `surgical_procedure_anatomical_location`, `surgical_procedure_date`, `surgical_procedure_findings`, `surgical_procedure_therapeutic`, `extent_of_residual_disease` |

```graphql
{ clinicalTrialData(study_short_name: "CMB") {
    targetedTherapyNodeCount targetedTherapyParticipantCount
    targetedTherapyNodeData { participant_ids targeted_therapy targeted_therapy_dose } } }
```

## Joining back

Every node row carries **`participant_ids`** (note: a String, not a list). Join clinical/treatment rows
to demographics or to a cohort (the `participant_id`s from `searchParticipants`/`participantOverview`)
on it. See [../examples/clinical_data.md](../examples/clinical_data.md).

## Notes

- These node-data types return **everything as Strings** (even ages, doses, dates) and split many
  values into `_unit`/`_original` companion fields — introspect the type if a field errors:
  `{ __type(name:"ClinicalDiagnosis"){ fields { name } } }` (with the `variables` key).
- The `NodeCount` vs `ParticipantCount` distinction matters: a study can have more diagnosis records
  than participants (e.g. CMB has 249 diagnoses for 248 participants).
- A study missing a node type simply omits it from `unique_node_types` and returns `0`/`[]`.
