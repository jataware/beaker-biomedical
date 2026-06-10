# Longitudinal clinical-trial data per study

Clinical-trial studies carry visits, cycles, adverse events, exams, and lesion measurements. Pull them
with the per-node `*NodeData(study_code)` queries. Uses the `icdc()` helper from
[quickstart.md](quickstart.md). Reference: [../references/CLINICAL.md](../references/CLINICAL.md).

## Step 1 — check what the study actually collected (counts vary a lot)

Many studies have **no** clinical-event data even when `clinical_study_type` is "Clinical Trial". Probe
first so you don't query empty nodes:

```python
icdc('{ clinicalDataNodeCounts(study_code: "COTC007B") '
     '{ cycle visit adverse_event physical_exam vital_signs disease_extent prior_therapy prior_surgery } }'
     )["clinicalDataNodeCounts"]
# {'cycle': 87, 'visit': 862, 'adverse_event': 0, 'physical_exam': 10016, 'vital_signs': 836,
#  'disease_extent': 1878, 'prior_therapy': 0, 'prior_surgery': 28}
```

`clinicalDataNodeCaseCounts(study_code)` gives the *number of distinct cases* per node instead of the
record count. Across ICDC, **COTC007B** is the richest for visits/exams/vitals/lesions; **PRECINCT01**
has adverse events (313); most other studies have none.

## Step 2 — pull a node's table

```python
# Lesion / RECIST-style assessments
icdc('{ diseaseExtentNodeData(study_code: "COTC007B", first: 1) '
     '{ case_id lesion_site lesion_description target_lesion longest_measurement date_of_evaluation } }'
     )["diseaseExtentNodeData"]
# [{'case_id': 'COTC007B-0101', 'lesion_site': 'Lymph node', 'lesion_description': 'Left prescapular',
#   'target_lesion': 'YES', 'longest_measurement': '2.5', 'date_of_evaluation': '2014-03-13'}]

# Vital signs (note: values come with split _unit/_original fields; introspect the type if unsure)
icdc('{ vitalSignsNodeData(study_code: "COTC007B", first: 1) '
     '{ case_id date_of_vital_signs body_temperature pulse modified_ecog } }')["vitalSignsNodeData"]

# Adverse events (use a study that has them)
icdc('{ adverseEventNodeData(study_code: "PRECINCT01", first: 1) '
     '{ case_id adverse_event_term adverse_event_grade date_of_onset attribution_to_research } }'
     )["adverseEventNodeData"]
# [{'case_id': 'PRECINCT01-UCD-IL15-001', 'adverse_event_term': 'Alanine aminotransferase (ALT), high',
#   'adverse_event_grade': '3', 'date_of_onset': '2018-11-21', 'attribution_to_research': 'Unlikely'}]
```

Other tables: `visitNodeData`, `cycleNodeData`, `physicalExamNodeData`, `priorSurgeryNodeData`,
`priorTherapyNodeData` (same `(study_code)` signature).

## Step 3 — join back to the patient

Every row carries `case_id`; join to demographics/diagnosis to analyze by breed, age, or cancer:

```python
ae = icdc('{ adverseEventNodeData(study_code: "PRECINCT01") '
          '{ case_id adverse_event_term adverse_event_grade } }')["adverseEventNodeData"]
case_ids = sorted({r["case_id"] for r in ae})
demo = icdc('{ casesInList(case_ids: %s) { case_id breed sex age } }'
            % str(case_ids).replace("'", '"'))["casesInList"]
# now merge ae + demo on case_id
```

## Caveats

- The `*NodeData` return types expose a **curated subset** of node fields and may rename them — if a
  field errors, introspect: `{ __type(name:"AdverseEventNodeData"){ fields { name } } }`.
- `agentNodeData`, `agentAdministrationNodeData`, `followUpNodeData`, `offTreatmentNodeData`,
  `offStudyNodeData` back nodes that are empty across current ICDC studies — expect `[]`.
- These return strings even for numbers (`longest_measurement: "2.5"`, `adverse_event_grade: "3"`).
