# Intended Behavior

In one call the agent satisfies the three first-call rules: POST-only, a body that includes the required `variables` key, and reading the faceted count from `subjects` (not `count`) inside `GroupCount`. An unfiltered `searchParticipants` is the totals call — 248 participants (1 study; also 1,140 specimens, 2,033 files, 42 targeted therapies), with race led by White 188 and Black or African American 44.

# Incorrect Behavior

The agent reports the endpoint as broken after the missing-`variables` 400, gives up on the `FieldUndefined` error from asking for `count`, or invents a breakdown.
