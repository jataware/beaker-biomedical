# Intended Behavior

The agent enumerates studies first via `programsProjectsStudies`/`diseasesAvailable` over the no-auth open path, returning multiple studies (not one) spanning the four analytical fractions — Proteome, Phosphoproteome, Glycoproteome, Metabolome (~12 studies for `disease_type = "Clear Cell Renal Cell Carcinoma"`) — with real `pdc_study_id`s (e.g. `PDC000127`, `PDC000128`, `PDC000413`) and case counts.

# Incorrect Behavior

The agent hardcodes a single study (e.g. CPTAC-3 / PDC000127), invents study IDs, or only suggests the portal/UI instead of enumerating via the API.
