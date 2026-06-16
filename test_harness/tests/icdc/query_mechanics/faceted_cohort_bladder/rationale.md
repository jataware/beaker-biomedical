# Intended Behavior

The agent reads the facet landscape with `searchCases(diagnosis: ["Bladder Cancer"])` (116 cases, 162 samples, 341 files across 5 studies, reading the `GroupCountES` `count` field), then lists actual rows via `caseOverview`/`casesInList` rather than stopping at the count, and reports the multi-study span and the facet breakdowns:

- studies (`filterCaseCountByStudyCode`): UBC02 56, UBC01 34, UBC03 16, TCL01 7, ORGANOIDS01 3 — two of which (TCL01, ORGANOIDS01) are not dedicated bladder studies
- top breeds: Scottish Terrier 42, Mixed Breed 21, Beagle 11, …
- disease sites: Bladder 51, `Bladder, Urethra` 41, … (compound multi-site values)

Real case ids include `ORGANOIDS01-OR-A`, `TCL01-Bliley`, and `UBC03-800-425`; `caseOverview` with `first: 200` returns all 116.

# Incorrect Behavior

The agent reports only a count with no rows, claims a single study, reads `subjects` instead of `count` on the `GroupCountES` buckets (a `FieldUndefined`/empty parse), or invents case ids.
