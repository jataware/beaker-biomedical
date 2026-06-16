# Intended Behavior

The agent returns the per-case detail that exists for UBC01 — 38 cases (34 Bladder Cancer + 4 Healthy Control) via `casesByStudyId`/`caseOverview`, each `caseDetail` carrying breed, sex, age, weight, stage, and `best_response` (Stable Disease 17, Partial Response 12, Not Applicable 4, Not Determined 3, Progressive Disease 2; 83 samples, 170 files) — and correctly reports the longitudinal event nodes as empty/not-loaded, ideally after a `clinicalDataNodeCounts` probe showing cycle, visit, adverse_event, and the rest at 0. Empty event nodes here are expected, not a bug (only COTC007B and PRECINCT01 carry that data).

# Incorrect Behavior

Because UBC01 is typed `Clinical Trial`, the agent claims it has visit/cycle/adverse-event rows (fabrication), reports the empty `*NodeData`/`clinicalDataNodeCounts` as an error or bug, retries indefinitely, or returns no per-case detail at all.
