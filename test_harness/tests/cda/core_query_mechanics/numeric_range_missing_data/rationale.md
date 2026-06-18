# Intended Behavior

The agent combines a numeric range with a missing-data filter — `summarize_subjects(match_all=['year_of_birth < 1950', 'cause_of_death != NULL', 'species = human'])` — reaching ≈328 subjects, with spaces around the operators and the CDA `NULL` keyword.

Verified live 2026-06-18. The `!= NULL` filter WORKS here even though `!=` is silently broken on string columns generally. Comparison counts with `species = human` and `year_of_birth < 1950`:
- no cause-of-death filter: 1,318 subjects
- `cause_of_death != NULL`: 328 subjects (the recorded-cause subset)
- `cause_of_death = NULL`: 990 subjects (missing)
- 328 + 990 = 1,318, so `!= NULL` correctly returns the complement of `= NULL`. `NULL` is a special-cased keyword that survives the otherwise-broken `!=`.

For contrast, on a plain string column `!=` is broken — `sex = male` and `sex != male` both return 77,125 — while on a numeric column it works — `year_of_birth = 1950` = 109 vs `year_of_birth != 1950` = 5,521. So the `!= NULL` idiom is the verified-working way to count "has a recorded cause of death"; enumerating cause_of_death values via `match_any` would also work but is unnecessary.

# Incorrect Behavior

The agent writes `year_of_birth<1950` without spaces around the operator (cdapython rejects this with a "does not conform to 'COLUMN_NAME OP VALUE' format" error), or reports the SQL idiom `IS NOT NULL` instead of the CDA `!= NULL` keyword, or guesses/enumerates cause_of_death values incorrectly.
