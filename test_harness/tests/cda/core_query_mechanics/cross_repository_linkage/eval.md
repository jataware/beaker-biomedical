# Expect

- **Expect:** `summarize_subjects(match_all=['subject_data_at_idc = true', 'subject_data_at_gdc = true'])`
  → **≈ 15,699 subjects** (~1.34M related files); maps IDC→imaging, GDC→sequencing.

# Failure Cases

- **Fail signs:** uses `upstream_source` (known-buggy) for linkage; a single keyword search.

# Automated Checks

```yaml
checks:
  - number:
      name: "idc_and_gdc_subjects"
      target: 15699
      tolerance_percent: 15
  - behavior: "used subject_data_at_idc = true AND subject_data_at_gdc = true (the *_data_at_* booleans)"
  - substring_any: ["imaging", "IDC"]
  - substring_any: ["genomic", "sequenc", "GDC"]
  - must_not_contain: ["upstream_source"]
```
