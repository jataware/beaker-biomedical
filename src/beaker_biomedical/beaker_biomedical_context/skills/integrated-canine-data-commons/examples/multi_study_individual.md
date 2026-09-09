# Map one dog across multiple studies

ICDC's distinctive feature: the same physical dog can be enrolled in more than one study, appearing as
a separate `case_id` in each. The **`canine_individual`** node ties those study-specific cases to one
underlying animal — so you can assemble *all* data for a dog regardless of which study contributed it.
18 of the 1,029 cases participate in multiple studies. Uses the `icdc()` helper from
[quickstart.md](quickstart.md).

## Find the multi-study cases

The `study_participation` facet flags them:

```python
ids = icdc('{ searchCases(study_participation: ["Multiple Study"]) { caseIds } }'
           )["searchCases"]["caseIds"]
print(len(ids), "cases participate in multiple studies")   # 18
```

## Resolve a case to its canine individual and all related data

`multiStudyCases(case_id)` returns the individual id plus every case / sample / file / study-file
belonging to that same dog:

```python
icdc('{ multiStudyCases(case_id: "OSA01-WLJ_054") '
     '{ individualId caseIds sampleIds fileIds studyFileIds } }')["multiStudyCases"]
# {'individualId': '0009',
#  'caseIds':   ['OSA01-WLJ_054', 'NCATS-COP01-CCB020018'],          # same dog, two studies
#  'sampleIds': ['OSA01-WLJ_054_T3', 'NCATS-COP01-CCB020018 0103', 'NCATS-COP01-CCB020018 0300'],
#  'fileIds':   ['57a5d3ed-...', '98cd9b94-...', '2468a2b2-...', '8f7d04c4-...', '510a380c-...'],
#  'studyFileIds': ['f1e155d4-...']}
```

So dog `0009` contributed an osteosarcoma case to **OSA01** and another to **NCATS-COP01** — pooling
their samples and files gives a fuller multi-platform picture of one animal.

## Use the pooled ids

The `caseIds` / `fileIds` feed the same downstream queries as any cohort:

```python
m = icdc('{ multiStudyCases(case_id: "OSA01-WLJ_054") { caseIds fileIds } }')["multiStudyCases"]

icdc('{ casesInList(case_ids: %s) { case_id study_code breed diagnosis age sex } }'
     % str(m["caseIds"]).replace("'", '"'))["casesInList"]

manifest = icdc('{ createManifest(uuid: %s) }'
                % str(m["fileIds"]).replace("'", '"'))["createManifest"]   # → CGC
```

## Traverse via the node graph instead

Equivalent through the auto-generated node queries (`case → canine_individual → case`):

```graphql
{ canine_individual(canine_individual_id: "0009") {
    canine_individual_id
    cases { case_id study { clinical_study_designation } } } }   # field is `cases` (plural)
```

This cross-study linkage — together with the `human_relevance` node that maps each study to the human
cancer it models (see [../references/CLINICAL.md](../references/CLINICAL.md)) — is what makes ICDC a
*comparative-oncology* resource rather than a set of isolated veterinary datasets.
