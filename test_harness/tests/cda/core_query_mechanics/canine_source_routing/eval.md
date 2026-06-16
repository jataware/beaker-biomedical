# Expect

- **Expect:** `summarize_subjects(data_source='ICDC')` (or `subject_data_at_icdc = true`) →
  **≈ 1,029 subjects / 3,599 files**; states CDA only *locates* it and analysis lives at the Integrated
  Canine Data Commons.

# Failure Cases

- **Fail signs:** claims CDA is human-only; tries to analyze in CDA.

# Automated Checks

```yaml
checks:
  - number:
      name: "icdc_subjects"
      target: 1029
      tolerance_percent: 15
  - substring_any: ["Integrated Canine Data Commons", "ICDC", "integrated-canine-data-commons"]
  - behavior: "stated CDA only locates the data and analysis happens at ICDC (did not analyze in CDA)"
  - must_not_contain: ["CDA is human-only", "no canine", "human subjects only"]
```
