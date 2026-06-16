# Intended Behavior

The agent runs `studyDemographics(study_short_name: ["PLCO"])` with the required `variables` key, selecting the `[GroupCounts]` fields with a `{ group subjects }` subselection and reading `subjects` (not `count`). PLCO has ~151,383 participants, median age 62 (range 42–78):

- sexes: male 74,703, female 76,680
- races: white 132,310, black or african american 7,563, asian 5,441, unknown 4,870, native hawaiian or other pacific islander 819, american indian or alaska native 380

# Incorrect Behavior

The agent reports NLST's demographics (the skill's worked example: median age 60, male 28,414 / female 20,446), selects `participant_sexes` as a scalar (`SubselectionRequired`) or uses `count` (`FieldUndefined`), omits the `variables` key (a hard error), or invents bucket numbers.
