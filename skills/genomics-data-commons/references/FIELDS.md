# GDC fields, `_mapping`, and `expand`

## Discovering valid fields

Every search/retrieval endpoint mirrors a `_mapping` endpoint that lists every valid field, the default
return set, and the available expand groups.

```bash
curl -s 'https://api.gdc.cancer.gov/files/_mapping' | jq .
```

Response sections:

| Key | Purpose |
|---|---|
| `_mapping` | All available fields keyed by endpoint-agnostic name (good for `filters`, not always for `fields`). |
| `defaults` | The fields automatically returned when `fields` is omitted. |
| `expand` | Valid arguments for the `expand=` parameter (field group names). |
| `fields` | All fields in endpoint-specific form. Use these for `fields=`. |
| `multi` | GDC-internal. Ignore. |
| `nested` | Fields that live inside arrays — typically `cases.diagnoses.*`, `cases.samples.*`, `cases.samples.portions.*`. |

Use Python to grep:

```python
import requests
m = requests.get("https://api.gdc.cancer.gov/files/_mapping").json()
print([f for f in m["fields"] if "workflow" in f])
```

## `fields` parameter

Comma-separated string. The response always includes `id`; other fields appear only if listed. Field
order in the response is undefined.

```
fields=file_id,file_name,cases.submitter_id,cases.samples.sample_type
```

For deeply nested fields, dot-notation reaches into arrays. The response preserves that nesting:

```json
"cases": [
  {"submitter_id": "TCGA-CK-4948",
   "samples": [{"sample_type": "Primary Tumor"}]}
]
```

## `expand` parameter

`expand` is a shortcut for "give me every field in this group." Available groups come from the
`expand` list in `/_mapping`. Common groups:

| Endpoint | Useful expand groups |
|---|---|
| `/cases` | `diagnoses`, `demographic`, `samples`, `samples.portions`, `samples.portions.analytes`, `samples.portions.analytes.aliquots`, `exposures`, `family_histories`, `follow_ups`, `summary` |
| `/files` | `cases`, `cases.samples`, `cases.samples.portions`, `annotations`, `analysis`, `analysis.input_files` |
| `/projects` | `summary`, `summary.experimental_strategies`, `summary.data_categories`, `program` |

`expand` and `fields` can be combined — `fields` limits scalar fields at the root level, `expand`
populates full nested groups underneath.

## Common case-level fields (high-value subset)

The `cases` document is the richest. These are field families that come up in almost every clinical
query:

- **Identity & state**: `case_id`, `submitter_id`, `state`, `created_datetime`, `updated_datetime`,
  `disease_type`, `primary_site`, `index_date`.
- **Demographic** (`demographic.*`): `age_at_index`, `cause_of_death`, `country_of_birth`,
  `days_to_birth`, `days_to_death`, `ethnicity`, `race`, `sex_at_birth`, `vital_status`,
  `year_of_birth`, `year_of_death`.
- **Diagnoses** (`diagnoses.*` — array): `age_at_diagnosis`, `ajcc_pathologic_stage`,
  `ajcc_pathologic_t/n/m`, `ann_arbor_clinical_stage`, `classification_of_tumor`, `days_to_diagnosis`,
  `days_to_last_follow_up`, `days_to_recurrence`, `figo_stage`, `morphology`, `primary_diagnosis`,
  `prior_malignancy`, `prior_treatment`, `tissue_or_organ_of_origin`, `tumor_grade`, `vital_status`.
  *Note: diagnoses is a list — see "Nested list semantics" below.*
- **Samples** (`samples.*` — array): `sample_id`, `submitter_id`, `sample_type`, `tissue_type`,
  `tumor_descriptor`, `preservation_method`, `is_ffpe`, `days_to_collection`,
  `composition`, `oct_embedded`.
- **Aliquots** (`samples.portions.analytes.aliquots.*` — array): `aliquot_id`, `submitter_id`,
  `analyte_type`, `concentration`.
- **Exposures, family_histories, follow_ups, treatments, molecular_tests** — each is its own nested
  array under the case.
- **Project rollup**: `project.project_id`, `project.program.name`, `project.primary_site`,
  `project.dbgap_accession_number`.

## Common file-level fields

- `file_id`, `file_name`, `file_size`, `md5sum`, `state`, `version`, `data_release`.
- `access` (`open`/`controlled`), `acl` (e.g. `["phs000178"]`).
- `data_category`, `data_type`, `data_format`, `experimental_strategy`, `platform`, `type`.
- `analysis.workflow_type`, `analysis.workflow_link`, `analysis.input_files.*`,
  `analysis.metadata.*`.
- `cases.case_id`, `cases.submitter_id`, `cases.project.project_id`, etc. — full case fields are
  reachable via `expand=cases` or dotted `fields`.

## Nested list semantics

Fields with `.` after a list-valued parent (`cases.diagnoses.*`, `cases.samples.*`) live in arrays. Two
implications:

1. **Filter behavior.** `cases.diagnoses.classification_of_tumor = metastasis` matches a case if *any*
   diagnosis in the list satisfies the condition. To drop only cases where *every* diagnosis matches,
   use `exclude`; to drop cases where *any* matches, use `excludeifany`. See [FILTERS.md](FILTERS.md).
2. **TSV flattening.** When `format=TSV`, nested arrays are flattened by index — column headers look
   like `cases.0.samples.0.sample_type`, `cases.0.samples.1.sample_type`, etc. For multi-row clinical
   data, prefer `format=JSON` + `expand`.

## Building a filter when you don't know the field

1. `GET <endpoint>/_mapping` → look in `fields` for something that matches the user's intent.
2. `GET <endpoint>?facets=<field>&size=0` → see all distinct values for that field.
3. Build the filter, run it, inspect `data.pagination.total` before you fetch the data.
