# Expect

- **Expect:** `column_values('diagnosis', filters='*melanoma*')` to see the variants, then
  `summarize_subjects(match_all=['diagnosis = *melanoma*'])` (cdapython expands `*`). The dominant term
  `Malignant melanoma` alone → **≈ 1,432 subjects** (≈1,229 of them at GDC); the full wildcard cohort is
  somewhat larger.

# Failure Cases

- **Fail signs:** `summarize_subjects(match_all=['diagnosis = melanoma'])` or `= Melanoma` (exact, no
  wildcard) → **0**, and the agent reports zero/stops instead of using `*melanoma*`.

# Automated Checks

```yaml
checks:
  - number:
      name: "melanoma_subjects"
      target: 1432
      tolerance_percent: 20
  - behavior: "used a wildcard ('*melanoma*') or discovered the free-text variants via column_values('diagnosis'), did not filter the exact 'melanoma'"
  - must_not_contain: ["0 subjects", "no melanoma", "not diagnosed with melanoma"]
```
