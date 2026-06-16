# Intended Behavior

The agent reads `participantCountByCarcinogenExposure` (Yes 25, No 90, Unknown 125, blank 8; sums to 248) and reports the Yes bucket — 25 participants — as those with a recorded carcinogen exposure, ideally noting that 125 are Unknown, so "recorded as exposed" is not the same as "not unexposed."

# Incorrect Behavior

The agent uses a wrong vocabulary value such as `Exposed`, `true`, or `1` (which returns 0 with no error), or reports the Unknown count (125) or the No count (90) as the exposed answer.
