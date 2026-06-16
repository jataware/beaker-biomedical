# Expect

- **Correct:** CDA does no analysis (no survival, no log-rank). It can locate the cohort and the
  GDC-resident subset; the curve + p-value come from GDC `/analysis/survival` (`genomic-data-commons`).

# Failure Cases

- **Fail signs:** claims to produce KM points/p-values from CDA.

# Automated Checks

```yaml
checks:
  - behavior: "declined to compute survival in CDA; routed the curve + p-value to GDC /analysis/survival (genomic-data-commons)"
  - substring_any: ["/analysis/survival", "genomic-data-commons", "GDC"]
  - must_not_contain: ["p-value from CDA", "CDA survival", "KM curve from CDA", "log-rank ... CDA"]
```
