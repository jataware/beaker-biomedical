# Clinical & biospecimen data

PDC's clinical model mirrors the GDC clinical dictionary (demographic, diagnosis, exposure, follow-up,
treatment) attached to **cases**, plus a biospecimen chain (sample → aliquot). The wrinkle is that
PDC splits these across **several queries** rather than exposing one big clinical endpoint.

## Two ways in: one case, or one study

### One case, everything — `case`
`case(case_submitter_id: "C3N-00386")` is the deep single-case query. In one (large) response it
returns `demographics`, `samples` (→ `aliquots` → `aliquot_run_metadata`), the full `diagnoses` block
(100+ staging/grade fields), `exposures`, `follow_ups`, and `treatments`. Accepts `case_id`,
`case_submitter_id`, `pdc_study_id`, or `study_id`. **Always POST** — the field selection is huge.

### One study's cases — the per-study family
For a whole study, PDC gives you one query per clinical sub-entity. The split exists because each
sub-entity is a separate (often multi-row) table per case:

| Query | Returns | Required ID |
|---|---|---|
| `clinicalPerStudy` | **Everything** (demographic + diagnosis fields + nested exposures/follow_ups/treatments/samples) in one non-paginated call | `pdc_study_id` |
| `clinicalMetadata` | Aliquot-level summary (morphology, primary_diagnosis, tumor_grade, tumor_stage) | `study_id` |
| `paginatedCaseDemographicsPerStudy` | demographics (ethnicity, gender, race, vital_status, age_at_index, …) | `study_id` + offset/limit |
| `paginatedCaseDiagnosesPerStudy` | diagnoses (primary_diagnosis, tumor_grade/stage, AJCC staging, morphology, …) | `study_id` + offset/limit |
| `paginatedCaseExposuresPerStudy` | exposures (tobacco/alcohol/environmental) | `study_submitter_id` + offset/limit |
| `paginatedCaseFollowUpsPerStudy` | follow-ups (disease response, ECOG/Karnofsky, recurrence, …) | `pdc_study_id` + offset/limit |
| `paginatedCaseTreatmentsPerStudy` | treatments (agents, dose, intent, outcome, …) | `pdc_study_id` + offset/limit |

Watch the **ID type per query** (some want `study_id`, some `pdc_study_id`, one wants
`study_submitter_id`) — resolve all three up front with `study`/`studyCatalog`. See
[ENTITIES.md](ENTITIES.md).

**Pick `clinicalPerStudy`** when you want the full clinical picture for a modest study in one call;
pick the paginated per-sub-entity queries when you want one slice (e.g. just diagnoses) or the study
is large enough that you need to page. The paginated ones are flagged *"may take a long time… huge
volume of data"* — use reasonable page sizes.

## Biospecimen: aliquot ↔ sample ↔ case

- `biospecimenPerStudy(pdc_study_id: …)` — flat rows of `aliquot_id sample_id case_id
  aliquot_submitter_id sample_submitter_id case_submitter_id aliquot_status case_status sample_status
  sample_type disease_type primary_site pool taxon`. This is the workhorse for **mapping quantitation
  columns (aliquots) back to patients (cases)**.
- `paginatedCasesSamplesAliquots(pdc_study_id: …, offset, limit)` — the nested case → sample → aliquot
  → aliquot_run_metadata tree, including sample biospecimen attributes (anatomic site, preservation
  method, weights, dimensions) and the labeled-channel metadata.

## Common gotchas

- **Each case can have multiple diagnoses / samples / follow-ups.** Treat the nested arrays as
  one-to-many; don't assume one row per case.
- **`disease_type` vs `primary_site` vs `tissue_or_organ_of_origin`.** `disease_type` is the
  histological diagnosis (e.g. *Clear Cell Renal Cell Carcinoma*); `primary_site` / `tissue_or_organ_of_origin`
  is the anatomical site (e.g. *Kidney*). Discovery queries (`diseasesAvailable`, `tissueSitesAvailable`)
  expose both — pick the one matching the user's phrasing. See [DISCOVERY.md](DISCOVERY.md).
- **Aliquot/sample IDs in processed files are internal.** The `*.sample.txt` files contain
  `biospecimen_submitter_id`s; link them to `case_submitter_id` via the biospecimen data (above) — not
  by string-guessing.
- Worked example: [examples/clinical_biospecimen.md](../examples/clinical_biospecimen.md).
