# Editing in place

How to make the fix without degrading the skill. Load this in step 3/4. The structural rules are
the same ones authoring follows — see [`../../skill-author/references/STRUCTURE.md`](../../skill-author/references/STRUCTURE.md)
and [`../../skill-author/references/BEST-PRACTICES.md`](../../skill-author/references/BEST-PRACTICES.md); this is the
improvement-specific guidance.

## Pick the smallest unit that fixes the cause

| The fix is… | Put it… |
|---|---|
| A cross-cutting fact that silently breaks answers everywhere | a **Critical rule** in `SKILL.md`, stated as a procedure with the verified number |
| A field/parameter/value/table detail | the relevant `references/<TOPIC>.md`; add a one-line note + pointer in `SKILL.md` only if it's load-bearing on every run |
| A multi-step recipe the agent keeps getting wrong | a new `examples/<task>.md`, with a one-line pointer (and load-trigger) from `SKILL.md` |
| A reference that exists but never gets opened | rewrite the `SKILL.md` pointer to say *when* to load it — don't move the content inline |

## Don't fatten SKILL.md

The strong temptation when a skill underperforms is to pile more emphasis into `SKILL.md`. Resist
it. `SKILL.md` is loaded every activation; every line there is a permanent tax. A new rule earns its
place only if it's cross-cutting and silent-failure-class. Detail goes to a reference; a recipe goes
to an example. If a rule you're adding runs past ~2–3 lines, the body belongs in a reference with a
one-line pointer left behind.

## State the fix as a verified procedure

- Write the *action*, not the observation: "pass the cohort as `case_filters`; `filters` only
  restricts which mutations are ranked" — not "the denominator is important".
- Attach the live-verified contrast where it makes the rule credible and self-checking: the right
  value and the wrong value the trap produces.
- Preserve any existing CRITICAL directives; add, don't soften.

## Re-baselining a drifted number

If the cause is "the count moved", confirm the new value live, update the reference/rule **and** the
matching `number` target in the test's `eval.yaml` (via `harness-test-author`), and note the new
value + date. Don't just widen the test tolerance until it can't fail — that hides the next drift.

## Confirm and watch for regressions

After the edit, re-run the exact failing query and confirm it's green, then run a couple of sibling
tests in the same service — a rule that fixes one case can perturb another (e.g. a new default that
helps query A but over-narrows query B). If a sibling regresses, the rule is too broad; scope it.
