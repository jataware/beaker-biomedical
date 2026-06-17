---
name: harness-test-author
description: >-
  Author a new evaluation test for the test_harness/ benchmark corpus — the
  tests/<service>/<category>/<test>/{test.md, rationale.md, eval.yaml} triad that grades a CRDC
  agent-skill's behavior. Use when adding or revising a benchmark case for cda/gdc/pdc/gc/icdc/
  ctdc/psdc: writing the prompt, designing machine-gradeable checks, live-verifying the ground
  truth, and validating with the harness CLI. To author or fix the skills themselves use
  skill-author / skill-improver.
compatibility: Run from test_harness/ in its uv venv (`uv pip install -e ".[test]"`). Live validation hits the public CRDC APIs and needs the relevant provider API key.
metadata:
  author: jataware
---

# Authoring a harness test

The harness runs a prompt through a model with one CRDC skill loaded, then grades the answer.
A test is a directory under `test_harness/tests/`:

```
tests/<service>/<category>/<test>/
├── test.md        # optional frontmatter (name, description) + the prompt (everything after it)
├── rationale.md   # # Intended Behavior / # Incorrect Behavior — design notes, NEVER graded
└── eval.yaml      # the machine-gradeable checks: a top-level `checks:` list
```

> **The one rule that governs everything: only `eval.yaml` is graded.** The parser reads `test.md`
> and `eval.yaml`; it never reads `rationale.md`, and the agent/judge never see it. If a behavior
> should affect the score it **must** be a check in `eval.yaml` — writing it in `rationale.md` does
> nothing. `rationale.md` exists to explain *why the checks are what they are*, for the next author.

`<service>` maps to a skill under `skills/` (`gdc`→genomics-data-commons, `cda`→cancer-data-aggregator,
`pdc`→proteomic-data-commons, `gc`→general-commons, `icdc`→integrated-canine-data-commons,
`ctdc`→clinical-translational-data-commons, `psdc`→population-sciences-data-commons). A test's ref is
`<service>:<category>/<test>`; `--query` also accepts the bare `<category>/<test>` or just the leaf.

## Procedure

1. **Place it.** Choose `service` (the skill under test), a `category` (reuse the existing taxonomy
   or add a descriptive one), and a leaf slug. See [references/CATEGORIES.md](references/CATEGORIES.md).
   Start from [assets/test-template/](assets/test-template/).

2. **Write `test.md`.** Frontmatter `name` and a `description` phrased as "This tests X"; then the
   prompt, handed to the agent **verbatim**. Write the prompt as a real user task, not a checklist —
   it must invite the trap you're testing for, not telegraph the answer.

3. **Draft `rationale.md` first — it's your design tool.** Under `# Intended Behavior`, the correct
   method and the ground-truth result. Under `# Incorrect Behavior`, the specific trap a weak agent
   falls into. You'll turn each of these into a check.

4. **Live-verify the ground truth.** Run the skill's own method against the live API to get the
   real number/IDs/count before baking it into a check. Counts drift — record what you got and when.
   See [references/GROUND-TRUTH.md](references/GROUND-TRUTH.md).

5. **Encode `eval.yaml`,** choosing check types that are *decidable from what the grader and judge
   actually see*: deterministic checks see only the final answer; the `behavior` judge sees the full
   transcript (including code); `count_at_least` sees only the final answer. This determines which
   assertions can be which type — see [references/CHECK-TYPES.md](references/CHECK-TYPES.md) and
   [references/WHAT-REACHES-THE-AGENT-AND-JUDGE.md](references/WHAT-REACHES-THE-AGENT-AND-JUDGE.md).

6. **Validate, then run.** From `test_harness/`:
   ```bash
   python -m harness.cli list  --query <service>:<category>/<test> --checks   # parses + shows the checks
   python -m harness.cli run   --query <service>:<category>/<test> --dry-run --show-prompt
   python -m harness.cli run   --query <service>:<category>/<test> --model claude-sonnet-4-6 --detail
   ```
   A strong model should pass; confirm each check fires on the evidence you intended. See
   [examples/validate_and_run.md](examples/validate_and_run.md).

## Check types at a glance

Deterministic (string/number match on the **final answer**, no LLM): `substring`, `substring_any`,
`substring_all`, `must_not_contain`, `regex`, `number`, `set_contains`. Judged by `--judge-model`:
`behavior` (reads the transcript — the workhorse for *method* claims) and `count_at_least`. Each is
a single-key YAML map. Full shapes, tolerances, and when-to-use are in
[references/CHECK-TYPES.md](references/CHECK-TYPES.md).

Encode the **trap** as `must_not_contain` (the wrong number / hallucinated capability). Use `number`
with a tolerance, never exact, for live counts. Use `behavior` for "which endpoint / filter slot /
decline-and-redirect", written as one literal decidable claim.

## Worked examples

- [examples/author_query_mechanics_test.md](examples/author_query_mechanics_test.md) — a normal count/query test, full triad.
- [examples/author_out_of_scope_test.md](examples/author_out_of_scope_test.md) — a decline-and-redirect "trap" test.
- [examples/author_file_handoff_test.md](examples/author_file_handoff_test.md) — files → DRS handoff, no download.
- [examples/validate_and_run.md](examples/validate_and_run.md) — the validate/iterate CLI loop.
