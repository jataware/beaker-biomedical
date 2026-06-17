# Exactly what each party sees

Write checks that are decidable from the evidence the grader actually has. Load this when deciding
a check's type, or when a check passes/fails for a reason you didn't expect. (`tests/README.md` is
the authoritative source; this is the author's-eye summary.)

```
test.md ─frontmatter─→ (reports only, not the agent)
        └─prompt──────→ AGENT  ┐
SKILL.md ──────────────→ AGENT  ├─→ final answer ─→ DETERMINISTIC checks (string/number on the answer)
skill file paths ──────→ AGENT  ┘                └→ JUDGE (behavior: whole transcript / count_at_least: answer)
eval.yaml ─────────────────────────────────────────→ grader (defines the checks)
rationale.md ───────────────────────────────────────→ nothing (humans only)
```

## The agent under test sees

- A fixed system role (autonomous data-analysis agent with a Python tool; "execute real code, never
  fabricate; if out of scope, say so and redirect; finish with an explicit final answer").
- The **entire `SKILL.md`** of the mapped skill, inlined.
- The **paths** of the skill's reference/example files (not their contents — it opens them itself
  via the `run_python` tool).
- The **prompt** from `test.md`, verbatim.

It never sees `eval.yaml`, `rationale.md`, or the test's `name`/`description`. So the prompt alone
must carry everything the agent needs to attempt the task — don't lean on the rationale to "explain"
the task.

## The deterministic grader sees

**Only the final-answer string.** `substring*`, `regex`, `number`, `set_contains`,
`must_not_contain` all match against that text. Implication: anything you want graded
deterministically must appear *in the answer the model writes*. If the right value is computed but
only printed in a tool call and never restated in the final answer, a `number`/`substring` check
will miss it. (This is fine and intended — it tests whether the agent reports its result.)

## The judge sees

One `complete()` call per semantic check, no tools, with a strict-grader system prompt:

- **`behavior`** → the assertion + the task prompt + the **full transcript**: the final answer *and*
  every step's emitted code with clipped stdout (whole thing clipped to ~18k chars). This is why
  `behavior` can verify *method* — which endpoint was called, which filter slot, whether the agent
  confirmed a value before filtering. It reads the code, not just the prose.
- **`count_at_least`** → the assertion + the task prompt + the **final answer only** (~12k chars).
  It cannot see the code, so it can only count what the answer enumerates.

The judge sees nothing else — no `description`, no `name`, no `rationale.md`.

## Consequences for authoring

- Put a **method** assertion in `behavior`, never a `substring` (the method is in the code, which
  only the judge sees).
- For a deterministic result check, make sure the prompt asks the agent to **state** the value, so
  it lands in the final answer.
- Don't smuggle grading intent into `rationale.md` or `description` — neither is read by any grader.
- Keep each `behavior` to one literal claim; the judge is conservative and reads compound sentences
  as "did *all* of this happen?", which is easy to fail spuriously.
