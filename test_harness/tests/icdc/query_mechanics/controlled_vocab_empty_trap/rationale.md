# Intended Behavior

When `searchCases(disease_site: ["Urinary Bladder"])` returns 0 cases with no `errors` (a clean HTTP 200 empty), the agent attributes it to a wrong controlled-vocabulary value rather than absent data, reads `caseCountByDiseaseSite` to find the real strings (`Bladder` 51, `Bladder, Urethra` 41, …; there is no "Urinary Bladder"), and rebuilds a non-empty cohort (≈51 for `Bladder`, or 116 via the broader `Bladder Cancer` diagnosis).

# Incorrect Behavior

The agent concludes "ICDC has no bladder data" (flatly wrong — there are 116 bladder-cancer cases), treats the empty list as a hard error, or never discovers the valid facet values.
