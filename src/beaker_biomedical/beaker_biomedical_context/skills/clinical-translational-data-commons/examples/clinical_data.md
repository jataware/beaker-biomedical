# Per-study clinical & clinical-trial data

`clinicalData` and `clinicalTrialData` return a study's full longitudinal records, grouped by node type
and pre-counted. Use the `ctdc()` helper from [quickstart.md](quickstart.md). Reference:
[../references/CLINICAL.md](../references/CLINICAL.md).

## Step 1 — see what nodes a study has

```python
cd = ctdc('''
{ clinicalData(study_short_name: "CMB") {
    unique_node_types
    diagnosisNodeCount diagnosisParticipantCount
    demographicNodeCount specimenNodeCount participantStatusNodeCount } }
''')["clinicalData"][0]
print(cd["unique_node_types"])
# ['diagnosis', 'demographic', 'exposure', 'specimen', 'participant_status']
print(cd["diagnosisNodeCount"], "diagnoses for", cd["diagnosisParticipantCount"], "participants")
# 249 diagnoses for 248 participants
```

`clinicalData(...)` returns a **list** — take `[0]`. Each node type has a `<node>NodeCount` (records)
and `<node>ParticipantCount` (distinct participants); a study can have more records than participants.

## Step 2 — pull a node's records

```python
dx = ctdc('''
{ clinicalData(study_short_name: "CMB") {
    diagnosisNodeData { participant_ids ctep_disease_term primary_disease_site histology } } }
''')["clinicalData"][0]["diagnosisNodeData"]
print(dx[0])
# {'participant_ids': 'MSB-05098', 'ctep_disease_term': 'Non-Small Cell Lung Carcinoma',
#  'primary_disease_site': 'Lung', 'histology': 'adenocarcinoma'}
```

Other `clinicalData` nodes: `demographicNodeData`, `exposureNodeData`, `specimenNodeData`,
`participantStatusNodeData`.

## Step 3 — treatment data (`clinicalTrialData`)

The clinical-trial side — targeted / non-targeted therapy, surgery, radiotherapy:

```python
ct = ctdc('''
{ clinicalTrialData(study_short_name: "CMB") {
    targetedTherapyNodeCount targetedTherapyParticipantCount
    surgeryNodeCount radiotherapyNodeCount
    targetedTherapyNodeData { participant_ids targeted_therapy targeted_therapy_dose } } }
''')["clinicalTrialData"][0]
print(ct["targetedTherapyNodeCount"], "targeted-therapy records for",
      ct["targetedTherapyParticipantCount"], "participants")
# 658 targeted-therapy records for 248 participants  (surgery 109, radiotherapy 282)
print(ct["targetedTherapyNodeData"][0])
# {'participant_ids': 'MSB-05098', 'targeted_therapy': 'Osimertinib', 'targeted_therapy_dose': '80'}
```

## Step 4 — join nodes on `participant_ids`

Every node row carries **`participant_ids`** (a String). Join across nodes — e.g. each participant's
diagnosis with their targeted therapies:

```python
from collections import defaultdict
dx = {r["participant_ids"]: r for r in ctdc('{ clinicalData(study_short_name:"CMB") '
        '{ diagnosisNodeData { participant_ids ctep_disease_term } } }')["clinicalData"][0]["diagnosisNodeData"]}
tx = defaultdict(list)
for r in ctdc('{ clinicalTrialData(study_short_name:"CMB") '
        '{ targetedTherapyNodeData { participant_ids targeted_therapy } } }'
        )["clinicalTrialData"][0]["targetedTherapyNodeData"]:
    tx[r["participant_ids"]].append(r["targeted_therapy"])

pid = "MSB-05098"
print(dx[pid]["ctep_disease_term"], "→", tx[pid])
# Non-Small Cell Lung Carcinoma → ['Osimertinib', ...]
```

## Notes

- Node-data fields come back as **Strings** (ages, doses, dates) with `_unit`/`_original` companions —
  introspect a type if a field errors: `ctdc('{ __type(name:"ClinicalTargetedTherapy"){ fields { name } } }')`.
- For *facet counts* of therapies/diagnoses across the cohort, use `searchParticipants` instead
  ([faceted_search.md](faceted_search.md)); `clinicalData`/`clinicalTrialData` give you the raw records.
