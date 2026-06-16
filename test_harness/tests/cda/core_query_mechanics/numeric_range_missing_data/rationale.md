# Intended Behavior

The agent combines a numeric range with a missing-data filter — `summarize_subjects(match_all=['year_of_birth < 1950', 'cause_of_death != NULL', 'species = human'])` — reaching ≈328 subjects, with spaces around the operators and the CDA `NULL` keyword.

# Incorrect Behavior

The agent writes `year_of_birth<1950` without spaces around the operator, or uses the SQL idiom `IS NOT NULL` instead of `!= NULL`.
