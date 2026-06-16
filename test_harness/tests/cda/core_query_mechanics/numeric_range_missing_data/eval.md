# Expect

- **Expect:** `summarize_subjects(match_all=['year_of_birth < 1950', 'cause_of_death != NULL', 'species = human'])`
  → **≈ 328 subjects**. Spaces around operators; `NULL` keyword.

# Failure Cases

- **Fail signs:** `year_of_birth<1950` (no spaces around `<`); SQL `IS NOT NULL`.

# Automated Checks

```yaml
checks:
  - number:
      name: "subjects"
      target: 328
      tolerance_percent: 15
  - behavior: "used 'year_of_birth < 1950' with spaces around the operator and 'cause_of_death != NULL' (CDA NULL keyword), filtered species = human"
  - must_not_contain: ["IS NOT NULL", "year_of_birth<1950"]
```
