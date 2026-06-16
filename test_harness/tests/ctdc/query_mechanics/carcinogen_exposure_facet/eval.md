# Expect

**Expected result (verified ground truth):**
- `participantCountByCarcinogenExposure` (sums to 248): **Yes 25, No 90, Unknown 125, blank 8.**
- "Have a recorded carcinogen exposure" = the **Yes** bucket = **25 participants**
  (`searchParticipants(carcinogen_exposure: ["Yes"]) → numberOfParticipants 25`). A good answer also
  notes that 125 are Unknown (status not recorded), so "recorded as exposed" ≠ "not unexposed."
**Pass:** reports **25** participants recorded as exposed (`Yes`), and ideally contextualizes the 90 No
/ 125 Unknown / 8 blank split.

# Failure Cases

**Trap:** the value vocabulary is `Yes` / `No` / `Unknown` / blank — **not** `Exposed`/`true`/`1`. A
wrong value (e.g. `carcinogen_exposure: ["Exposed"]`) returns **0 with no error**. Also: the agent must
read the **`Yes` bucket** for "have a recorded exposure," not the `Unknown` bucket (the largest) or a
sum.
**Fail:** returns 0 after a wrong vocabulary value, or reports the Unknown count (125) / the No count
(90) as the "exposed" answer.

# Automated Checks

```yaml
checks:
  - number:
      name: "carcinogen_exposure_yes"
      target: 25
      tolerance_absolute: 3
  - number:
      name: "carcinogen_exposure_unknown"
      target: 125
      tolerance_percent: 10
  - substring: "25"
  - behavior: "used the `Yes` bucket / `carcinogen_exposure: [\"Yes\"]`, not `Unknown` or a sum"
  - must_not_contain: ["125 participants have a recorded", "90 participants were exposed"]
```
