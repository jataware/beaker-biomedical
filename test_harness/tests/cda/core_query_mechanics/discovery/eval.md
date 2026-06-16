# Expect

- **Expect:** `column_values('vital_status')` first (values are lowercase `alive`/`dead`), then
  `summarize_subjects(match_all=['vital_status = dead', 'species = human'])` → **≈ 8,556 subjects**.

# Failure Cases

- **Fail signs:** guesses `Deceased`/`DEAD`/`Dead` without checking (exact match is case-insensitive so
  `Dead` happens to work, but the agent should *verify*, not assume); looks for vital status on the
  `subject` table (it's on `observation`).

# Automated Checks

```yaml
checks:
  - number:
      name: "deceased_subjects"
      target: 8556
      tolerance_percent: 15
  - behavior: "called column_values('vital_status') to confirm the value (lowercase 'dead') before filtering"
  - behavior: "filtered on species = human in addition to vital_status"
  - substring_any: ["dead", "deceased"]
```
