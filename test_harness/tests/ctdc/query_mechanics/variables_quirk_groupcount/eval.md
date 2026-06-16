# Expect

**Traps:**
1. Sending the body **without a `variables` key** → HTTP 400 `Cannot invoke "java.util.Map.keySet()"`,
   which an agent may misread as "endpoint down" instead of "add `variables: {}`".
2. Asking for `count` inside the facet bucket → `Validation error (FieldUndefined@... Field 'count' in
   type 'GroupCount' is undefined)`. The field is **`subjects`**.
**Expected result (verified ground truth):**
- **248 participants** (1 study; also 1,140 specimens, 2,033 files, 42 targeted therapies).
- Race (`participantCountByRace`, per-participant, sums to 248): **White 188, Black or African American
  44, Asian 6, Unknown 4, Not Reported 3, American Indian or Alaska Native 2, Native Hawaiian or other
  Pacific Islander 1.**
**Pass:** reports 248 participants and a race breakdown led by White (~188) and Black or African
American (~44), having used `subjects` (not `count`) and a body with the `variables` key.

# Failure Cases

**Fail:** reports the endpoint as broken after the missing-`variables` 400, uses `count` and gives up on
the FieldUndefined error, or invents a breakdown.

# Automated Checks

```yaml
checks:
  - number:
      name: "total_participants"
      target: 248
      tolerance_absolute: 2
  - number:
      name: "race_white"
      target: 188
      tolerance_percent: 10
  - number:
      name: "race_black"
      target: 44
      tolerance_percent: 10
  - substring_all: ["white", "black or african american", "asian"]
  - behavior: "request body included a `variables` key (even `{}`)"
  - behavior: "read the facet count from the `subjects` field, not `count`"
  - must_not_contain: ["endpoint is down", "service unavailable", "api is offline"]
```
