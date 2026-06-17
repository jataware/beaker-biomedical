# Worked test: a query-mechanics count

The full triad for a normal "count, the right way" test — modeled on
`tests/cda/core_query_mechanics/discovery`. The trap here is value-casing: the agent must *confirm*
the controlled-vocabulary value before filtering, not guess it.

## test.md

```markdown
---
name: "Discovery + value casing (`vital_status`)"
description: "This tests the column_values → filter loop on a column the examples never touch, confirming the lowercase `dead` value before filtering."
---
Using CDA, how many human subjects are recorded as deceased? Show me how you confirmed the value you filtered on.
```

The prompt invites the trap ("deceased" — but the stored value is lowercase `dead`) and explicitly
asks the agent to show its confirmation, so the method lands in the transcript.

## rationale.md (design tool — not graded)

```markdown
# Intended Behavior
The agent inspects `column_values('vital_status')` to confirm the value is lowercase `dead`
(alongside `alive`), then filters `summarize_subjects(match_all=['vital_status = dead',
'species = human'])` to reach ≈ 8,556 subjects (live-verified 2026-06).

# Incorrect Behavior
Guesses `Deceased`/`DEAD`/`Dead` without checking the vocabulary, or looks for vital status on the
`subject` table when it lives on `observation`.
```

## eval.yaml

```yaml
checks:
  - number: {name: deceased_subjects, target: 8556, tolerance_percent: 15}
  - behavior: "called column_values('vital_status') to confirm the value (lowercase 'dead') before filtering"
  - behavior: "filtered on species = human in addition to vital_status"
  - substring_any: ["dead", "deceased"]
```

## Why each check is the type it is

- `number` (tolerance, not exact) — the count is in the answer and drifts with releases.
- The two `behavior` checks — "confirmed the value first" and "added the species filter" are
  *method* claims, visible only in the code, so they must be judged on the transcript. Each is one
  literal claim, kept separate.
- `substring_any` — a cheap deterministic guard that the answer actually talks about the right
  vital-status value.

Note there's no `must_not_contain` here because the casing trap (`Dead`) happens to still match
case-insensitively — the discriminating signal is the *behavior* (did it confirm?), so that's where
the check lives.
