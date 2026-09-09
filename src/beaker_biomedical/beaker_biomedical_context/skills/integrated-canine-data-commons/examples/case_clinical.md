# One case's clinical record

Once you have a `case_id` (from [faceted_search.md](faceted_search.md), `casesByStudyId`, or
`globalSearch`), pull its clinical detail. Uses the `icdc()` helper from [quickstart.md](quickstart.md).

## Fast path: `caseDetail` (flattened summary)

`caseDetail(case_id)` pre-joins program → study → arm/cohort + demographic + enrollment + primary
diagnosis into one flat object — the quickest "tell me about this patient" call.

```python
icdc('''
{ caseDetail(case_id: "COTC022-2213") {
    case_id program_acronym clinical_study_designation
    breed sex patient_age_at_enrollment neutered_indicator weight
    disease_term stage_of_disease primary_disease_site best_response
    site_short_name date_of_registration patient_subgroup } }
''')["caseDetail"]
# {'case_id': 'COTC022-2213', 'program_acronym': 'COP', 'clinical_study_designation': 'COTC022',
#  'breed': 'Bulldog', 'sex': 'Male', 'patient_age_at_enrollment': 8.8, 'neutered_indicator': 'Yes',
#  'weight': 31.3, 'disease_term': 'Osteosarcoma', 'stage_of_disease': 'Not Determined',
#  'primary_disease_site': 'Bone (Appendicular)', 'best_response': 'Progressive Disease',
#  'site_short_name': 'VT', ...}
```

## Full path: node queries with traversal

For fields not in `caseDetail`, query the `case` node and nest the related nodes (the relationship
field names mirror the data model — see [../references/ENTITIES.md](../references/ENTITIES.md)):

Relationship fields on `case` are named after the model edges and are **plural where many-valued** —
`diagnoses`, `samples`, `files`, `visits`, `cycles` (lists); `study`, `study_arm`, `cohort`,
`demographic`, `enrollment`, `canine_individual` (single):

```python
icdc('''
{ case(case_id: "COTC022-2213") {
    case_id patient_id
    study { clinical_study_designation clinical_study_name clinical_study_type }
    study_arm { arm arm_description }
    cohort { cohort_description cohort_dose }
    demographic { breed additional_breed_detail sex neutered_indicator
                  patient_age_at_enrollment weight date_of_birth }
    diagnoses { disease_term primary_disease_site stage_of_disease histological_grade
                histology_cytopathology date_of_diagnosis best_response concurrent_disease
                pathology_report treatment_data follow_up_data }
    enrollment { date_of_registration date_of_informed_consent site_short_name
                 veterinary_medical_center patient_subgroup }
    samples { sample_id sample_site physical_sample_type tumor_grade }
    files { file_name file_type file_format file_size uuid } } }
''')["case"]   # note: case(...) returns a LIST, take [0]
```

`study_arm` / `cohort` are `null` for cases not assigned to one. `pathology_report` /
`treatment_data` / `follow_up_data` on diagnosis are **availability flags** (Yes/No), not the content.

## Cases of a study, or a rich list for known ids

```python
# every case of a study (study_id == clinical_study_designation)
icdc('{ casesByStudyId(study_id: "OSA01", first: 500) { case_id patient_id } }')["casesByStudyId"]

# rich overview rows for an explicit id set (e.g. caseIds from searchCases)
icdc('{ casesInList(case_ids: ["COTC022-2213","OSA01-..."]) '
     '{ case_id study_code breed diagnosis age sex disease_site } }')["casesInList"]
```

## Next

- This dog's other study enrollments → [multi_study_individual.md](multi_study_individual.md).
- This case's samples & files → [files_and_download.md](files_and_download.md).
- Longitudinal trial events (visits, adverse events, vitals) for the study →
  [clinical_node_data.md](clinical_node_data.md).
