# Feedback signals

The two evidence sources for improving a skill, and how to read each. Load this in step 1.

## Signal A — the harness (structured, repeatable)

The eval harness is the primary signal: it runs a real prompt through a model with the skill
loaded and grades the result, so a failing check is concrete, reproducible evidence of a gap.

From `test_harness/`:

```bash
# one service, every check result printed (not just failures)
python -m harness.cli run --service gdc --model claude-sonnet-4-6 --detail

# one test, full capture for inspection
python -m harness.cli run --query gdc:query_mechanics/mutation_frequency_denominator \
    --model claude-sonnet-4-6 -o report.json
```

What to read:

- **Which check failed, and its type.** The type tells you the *kind* of gap (see
  [DIAGNOSIS.md](DIAGNOSIS.md)): a `behavior` fail is a method problem; a `number`/`set_contains`
  fail is a wrong-value problem; a `must_not_contain` fail means the agent walked into the trap.
- **The per-step `code_trace`** (in the JSON report, or streamed with `-j 1`). This is the gold:
  it shows the *actual* calls the agent made. Compare them to what the skill told it to do. The gap
  is usually visible as "the agent did X because the skill implied X, but the right call was Y."
- **The `transcript` / final answer.** Did the agent compute the right thing but fail to state it?
  That's a different fix (prompt/answer-shaping) than computing the wrong thing.

Re-run after editing to confirm the fix. Because variance is real, run a failing test 2–3×: a check
that fails once in three is a fragile test or a borderline rule, not a clean gap.

## Signal B — a live probe

When you suspect the skill's *facts* are stale or wrong (a field renamed, a count moved, an endpoint
changed behavior), go straight to the API: run the skill's own example code and diff reality against
what the skill claims.

```python
import requests
# The skill says facet field X returns buckets keyed by `count`. Does it?
r = requests.post("<base>/<endpoint>", json={...})
print(r.status_code, r.json())   # -> compare to the skill's stated shape/values
```

Use this signal when there's no test covering the behavior yet (and consider writing one with
`harness-test-author` so the fix stays regression-protected), or to confirm the *correct* value
before you edit a rule.

## Which signal, when

- A test is failing → start with the harness; the trace localizes the gap.
- A user reported a wrong result with no test → live-probe to establish ground truth, fix, then add
  a test.
- You changed a skill and want to be sure nothing regressed → harness, run the whole service suite.
