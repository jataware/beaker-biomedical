# Intended Behavior

The agent first inspects `column_values('vital_status')` to confirm the value is the lowercase `dead` (alongside `alive`), then filters `summarize_subjects(match_all=['vital_status = dead', 'species = human'])` to reach ≈8,556 subjects.

# Incorrect Behavior

The agent guesses `Deceased`, `DEAD`, or `Dead` without checking the vocabulary — exact match is case-insensitive so `Dead` happens to work, but the value should be verified, not assumed — or looks for vital status on the `subject` table when it actually lives on `observation`.
