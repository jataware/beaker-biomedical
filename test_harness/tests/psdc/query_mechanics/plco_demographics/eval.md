# Expect

**Traps:**
1. Selecting `participant_sexes` as a scalar → `Validation error (SubselectionRequired ... type
   '[GroupCounts]')`.
2. Using `count` instead of `subjects` for the bucket → `Validation error (FieldUndefined ... Field
   'count' in type 'GroupCounts' is undefined)`.
3. Omitting the `variables` key → hard error (`...because "variables" is null`), not an empty result.
4. Reporting NLST's numbers (median age 60, male 28414 / female 20446) — the skill's own worked
   example — instead of PLCO's.
**Expected result (verified ground truth, 2026-06-11):**
- `number_of_participants` = **151383**; `participant_median_age` = **62**; age range **42 – 78**.
- `participant_sexes`: **male 74703**, **female 76680**.
- `participant_races`: **white 132310**, black or african american **7563**, asian **5441**, unknown
  **4870**, native hawaiian or other pacific islander **819**, american indian or alaska native **380**.
- (bonus) `participant_ethnicities`: not hispanic or latino 148417, hispanic or latino 2966.
**Pass:** reports PLCO's ~151k participants, median age ~62, and the sex + race breakdown with the right
female-majority sex split and white-dominant race split, using `subjects` bucket counts.

# Failure Cases

**Fail:** returns NLST's demographics, reports `count`/scalar-field errors as the answer, omits the
`variables` key, or invents bucket numbers.

# Automated Checks

```yaml
checks:
  - number:
      name: "PLCO_participants"
      target: 151383
      tolerance_percent: 5
  - number:
      name: "PLCO_median_age"
      target: 62
      tolerance_absolute: 2
  - number:
      name: "PLCO_female"
      target: 76680
      tolerance_percent: 5
  - number:
      name: "PLCO_male"
      target: 74703
      tolerance_percent: 5
  - number:
      name: "PLCO_white"
      target: 132310
      tolerance_percent: 5
  - substring_all: ["female", "white"]
  - must_not_contain: ["28414", "20446"]
  - behavior: "queried studyDemographics with study_short_name \"PLCO\" and selected { group subjects } on the GroupCounts fields (did not select a scalar"
```
