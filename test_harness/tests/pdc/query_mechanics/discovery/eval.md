# Expect

**Expected result:**
- Returns **multiple** studies (not one), spanning **4 analytical fractions**: Proteome,
  Phosphoproteome, Glycoproteome, Metabolome (~12 studies total for `disease_type = "Clear Cell Renal
  Cell Carcinoma"` via `programsProjectsStudies`).
- Names real `pdc_study_id`s (e.g. `PDC000127`, `PDC000128`, `PDC000413`, `PDC000414`, …).
- Reports case counts (e.g. via `diseasesAvailable`: *CPTAC3 Discovery and Confirmatory* = 212 ccRCC
  cases; the `study` query reports `PDC000127` `cases_count` = 124).
**Pass:** ≥ 2 distinct studies found, correct discovery query used, real IDs + counts.

# Failure Cases

**Trap:** hardcoding one study ("CPTAC-3 / PDC000127"). The skill requires enumerating first.
**Fail:** single study returned, invented study IDs, or only the portal/UI suggested.

# Automated Checks

```yaml
checks:
  - count_at_least:
      name: "studies"
      min: 2
  - set_contains:
      name: "study_ids"
      members: ["PDC000127"]
  - regex:
      name: "returned study ids"
      pattern: 'PDC\d{6}'
  - number:
      name: "PDC000127_cases"
      target: 124
      tolerance_percent: 10
  - substring_any: ["Proteome", "Phosphoproteome", "Glycoproteome", "Metabolome"]
  - behavior: "enumerated studies via a discovery query (programsProjectsStudies / diseasesAvailable), did NOT hardcode a single study"
  - must_not_contain: ["the only study", "single study", "CPTAC-3 is the one study"]
```
