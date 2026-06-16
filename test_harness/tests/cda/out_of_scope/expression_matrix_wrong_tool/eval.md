# Expect

- **Correct:** CDA does not serve expression matrices; it locates the cohort/files, then hands off to
  GDC `/gene_expression/values` (`genomic-data-commons`).

# Failure Cases

- **Fail signs:** claims a `cdapython` call returns a genes×samples matrix.

# Automated Checks

```yaml
checks:
  - behavior: "stated CDA does not serve expression matrices; located the cohort then routed to GDC /gene_expression/values"
  - substring_any: ["gene_expression/values", "genomic-data-commons", "GDC"]
  - must_not_contain: ["cdapython", "CDA returns the matrix", "genes×samples from CDA", "genes x samples from CDA"]
```
