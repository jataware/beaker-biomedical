---
name: skill-improver
description: >-
  Improve an existing Agent Skill in place from live feedback — diagnose why an agent using the
  skill produced a wrong or weak result, locate the right file to change, make a minimal edit, and
  re-verify. Use when a skill is already written and you have evidence it underperforms: a failing
  test_harness/ check, a wrong live-API result, or an observed bad agent run. To author a skill from
  scratch use skill-author; to write the tests that produce the feedback use harness-test-author.
compatibility: Run from test_harness/ for the harness signal (its uv venv + provider API key). Network access to re-probe a source API.
metadata:
  author: jataware
---

# Improving a skill from live feedback

A live skill underperforms because of a **gap in the skill**, a **limitation of the model**, or a
**bad test**. This skill is the loop for the first case: turn observed failure into the smallest
edit that fixes it, and prove the fix. Keep the same progressive-disclosure discipline the skill was
written under — see [`skill-author`'s BEST-PRACTICES.md](../skill-author/references/BEST-PRACTICES.md) and
[STRUCTURE.md](../skill-author/references/STRUCTURE.md).

## The loop

1. **Get a feedback signal.** Either:
   - **The harness** (preferred — it's structured and repeatable): from `test_harness/`, run
     `python -m harness.cli run --service <svc> --detail` and read the failing checks plus the
     per-step trace; or `-o report.json` for the full `code_trace`/`transcript`.
   - **A live probe**: re-run the skill's own example code against the source API and diff what
     happened against what the skill claims.

   See [references/FEEDBACK-SIGNALS.md](references/FEEDBACK-SIGNALS.md).

2. **Diagnose the cause.** Is it a **skill gap** (a missing rule, a wrong field name, an ambiguous
   instruction, a missing example, a pointer that never said *when* to load a reference) or a
   **model limitation** (the model ignored a rule that *is* clearly stated)? Only the first is fixed
   by editing the skill. Map the symptom to a cause — and to the file that owns it — with
   [references/DIAGNOSIS.md](references/DIAGNOSIS.md).

3. **Locate the fix at the smallest level.** A cross-cutting fact that silently breaks answers →
   a **Critical rule** in `SKILL.md`. A field/parameter/table detail → the relevant
   `references/*.md`. A recurring multi-step recipe the agent keeps getting wrong → a new
   `examples/*.md` with a one-line pointer. Do **not** fatten `SKILL.md` with detail that belongs in
   a reference. See [references/EDIT-IN-PLACE.md](references/EDIT-IN-PLACE.md).

4. **Edit minimally, with the verified fact attached.** State the surprise as a procedure and bake
   in the number/field you verified live. Change as little as possible; one fix per cause.

5. **Re-verify.** Re-run the same harness query (or re-probe) and confirm the check now passes.
   Re-run a couple of sibling tests to catch regressions. Run-to-run variance is real even at
   temperature 0 — repeat and average before declaring victory.

## Principles

- **Don't encode a model limitation as a skill rule.** If the rule is already stated plainly and the
  model still ignored it, more words rarely help — note it and stop, rather than bloating the skill.
- **Fix the smallest unit.** Prefer editing one reference line or adding one example over rewriting
  `SKILL.md`. The skill must stay terse (the rule it was built under).
- **A failure might be the test's fault.** If the agent's behavior is actually correct and the check
  is wrong (too strict, wrong type, grading evidence never put in the final answer), fix the test
  with `harness-test-author` — don't distort the skill to satisfy a bad check.
- **Every factual change is live-verified.** Never "fix" a field name or number from memory; confirm
  it against the API first (the same discipline as authoring).

## Worked examples

- [examples/improve_from_harness_failure.md](examples/improve_from_harness_failure.md) — a failing `behavior`/`number` check → trace → minimal edit → green.
- [examples/improve_from_live_probe.md](examples/improve_from_live_probe.md) — a live-API surprise → a new Critical rule + reference.
- [examples/fix_a_trap_test.md](examples/fix_a_trap_test.md) — the agent took the trap (`must_not_contain` fired) → an explicit anti-pattern rule.
