# Intended Behavior

The agent first inspects `column_values('vital_status')` to confirm the value is the lowercase `dead` (alongside `alive`), then filters `summarize_subjects(match_all=['vital_status = dead', 'species = human'])` to reach ≈8,556 subjects.

Verified live 2026-06-18: `column_values('vital_status')` returns `dead` (14,171), `alive` (32,124), `<NA>` (326,858); `column_values('species')` returns `human` (103,225). `summarize_subjects(match_all=['vital_status = dead', 'species = human'])` = 8,556 (`vital_status = dead` alone = 9,045, so the `species = human` filter is load-bearing).

# Incorrect Behavior

The agent guesses `Deceased`, `DEAD`, or `Dead` without checking the vocabulary — exact match is case-insensitive so `Dead` happens to work, but the value should be verified, not assumed — or looks for vital status on the `subject` table when it actually lives on `observation`.
