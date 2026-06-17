# Diagnosis: symptom → cause → file

Map an observed failure to its cause and to the file that owns the fix. Load this in step 2.

## First fork: skill gap, model limit, or bad test?

- **Skill gap** — the skill is missing, wrong, ambiguous, or buried. *Editing the skill fixes it.*
  This is the common case and the rest of this file is about it.
- **Model limitation** — the rule is stated plainly and correctly, and the model ignored it anyway.
  More words usually won't help; note it and stop. (Occasionally a *reframing* — moving a buried
  rule up to a Critical rule, or making it a procedure instead of a declaration — does help; try
  that once, not a wall of emphasis.)
- **Bad test** — the agent's behavior was actually correct and the check is wrong (too strict, wrong
  type, or grading something the agent never put in the final answer). Fix the test with
  `harness-test-author`; don't distort the skill.

Read the trace before deciding. "The agent never tried the right call" points to a gap; "the agent
made the right call but the check looked for the wrong string" points to a bad test.

## Symptom → cause → where to edit

| Failing signal | Likely cause | Fix lands in |
|---|---|---|
| `behavior` fail — agent used the wrong method/endpoint/filter slot | the correct method isn't stated, or is buried below the wrong default | a **Critical rule** in `SKILL.md` (cross-cutting) and/or the topic `references/*.md` |
| `number` / `set_contains` fail — right method, wrong value | wrong field, wrong filter, or the denominator trap (`case_filters` vs `filters`) | the topic `references/*.md` + a Critical rule naming the field/slot |
| `must_not_contain` fired — agent took the trap | the trap isn't called out as an anti-pattern | a Critical rule stating the trap explicitly ("don't default to TCGA"; "don't divide by the GDC-wide denominator") |
| out-of-scope test fail — agent fabricated instead of declining | the scope boundary / decline-redirect isn't stated | a "scope & redirect" rule in `SKILL.md` |
| agent never opened the reference that had the answer | the `SKILL.md` pointer didn't say *when* to load it | rewrite the pointer with a load-trigger (see `skill-author`'s `references/STRUCTURE.md`) |
| agent computed it right but didn't report it | the answer-shaping expectation isn't stated | a one-line "state the number/IDs explicitly" cue (or it's a bad test) |
| stale field name / count / endpoint behavior | the source drifted from the skill | live-verify, then correct the reference + any Critical rule that cites it |

## The canonical gap

The mutation-frequency denominator (GDC) is the archetype of a *silent plausible-wrong-answer* gap:
the agent passes the cohort as `filters` instead of `case_filters`, the denominator stays GDC-wide,
and the frequency collapses to a believable-looking but wrong number. Nobody guesses the fix; it has
to be a Critical rule with the verified contrast (16.67% via `case_filters` vs 0.08% via `filters`).
When you find a failure of this shape — right shape of answer, wrong value, no error raised — it's
almost always worth a Critical rule, not just a reference note.

## After diagnosis

Carry the cause and the chosen file into step 3/4. One cause → one minimal edit. If you've found
several causes, fix and re-verify them one at a time so you know which edit moved which check.
