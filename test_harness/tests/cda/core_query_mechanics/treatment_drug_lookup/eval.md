# Expect

- **Expect:** `column_values('therapeutic_agent', filters='*cisplatin*')` → `Cisplatin`, then
  `summarize_subjects(match_all=['therapeutic_agent = Cisplatin'])` → **≈ 1,168 subjects**.

# Failure Cases

- **Fail signs:** invents a `drug`/`treatment` column; reports the value-occurrence count (≈1,270)
  instead of the distinct-subject count (≈1,168).

# Automated Checks

```yaml
checks:
  - number:
      name: "cisplatin_subjects"
      target: 1168
      tolerance_percent: 15
  - substring: "Cisplatin"
  - behavior: "used the therapeutic_agent column (discovered via column_values), not an invented drug/treatment column"
  - must_not_contain: ["1270", "1,270"]
```
