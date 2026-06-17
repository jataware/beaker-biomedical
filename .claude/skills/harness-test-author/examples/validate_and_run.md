# Validate and run a new test

The loop after you've written the triad. Run everything from `test_harness/`.

## 1. Does it parse? (no API calls)

```bash
python -m harness.cli list --query gdc:query_mechanics/my_new_test --checks
```

Lists the test with its parsed checks. If the test doesn't appear, the directory name / placement is
wrong; if a check is missing or malformed, `eval.yaml` didn't parse the way you intended. Fix until
the printed checks match what you wrote.

Common parse issues:
- A check item that isn't a single-key map (e.g. two keys under one `-`).
- `number` without a tolerance key (it'll default to exact — usually not what you want for a count).
- An inline list written as a block where a scalar was expected, or vice-versa.

## 2. Does the prompt assemble correctly? (no API calls)

```bash
python -m harness.cli run --query gdc:query_mechanics/my_new_test --dry-run --show-prompt
```

Shows the exact system + user message the agent will get (full `SKILL.md` + reference paths + your
prompt) and the model routing — for free. Confirm the prompt reads as a real task and carries
everything the agent needs (it never sees `rationale.md`).

## 3. Does a strong model pass it? (live)

```bash
python -m harness.cli run --query gdc:query_mechanics/my_new_test --model claude-sonnet-4-6 --detail
```

`--detail` prints every check result, not just failures. You're checking two things:

1. **A capable model passes.** If it doesn't, either the skill has a real gap (a job for
   `skill-improver`) or your check is wrong — too strict, the wrong type, or grading evidence the
   agent never put in the final answer.
2. **The checks fire on the evidence you intended.** Read the trace. A `behavior` should pass
   *because* the code did the thing, not incidentally. A `must_not_contain` should be capable of
   failing — sanity-check it against a known-bad answer if unsure.

Add `-o report.json` to capture the full per-step `code_trace` and `transcript` for inspection.

## 4. Iterate

Run-to-run variance is real even at temperature 0; repeat a couple of times before concluding a test
is stable. Tighten prompts that are ambiguous, split any `behavior` that's really two claims, and
re-baseline a `number` target if the live count has drifted from what you recorded.
