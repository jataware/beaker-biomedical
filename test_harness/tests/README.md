# CRDC skill benchmark corpus

This is the **answer-key corpus** the evaluation harness grades against: one directory per
test, holding the prompt the agent is given and the checks its answer is graded against.
For how to *run* the harness see [`../README.md`](../README.md); this file documents the
corpus format and — precisely — **what data reaches the agent and the judge at every point.**

## Layout

```
tests/
├── README.md                     ← you are here
└── <service>/                    ← one per CRDC skill: cda, gdc, pdc, gc, icdc, ctdc, psdc
    └── <category>/               ← a descriptive grouping (e.g. core_query_mechanics, file_handoff)
        └── <test>/               ← one test
            ├── test.md           ← optional frontmatter + the prompt
            ├── rationale.md      ← # Intended / # Incorrect Behavior prose (humans only, never parsed)
            └── eval.yaml         ← the machine-gradeable checks (a top-level `checks:` list)
```

`<service>` maps to a skill under `../../skills/` via `harness/config.py:SERVICE_TO_SKILL`. A
test's ref is `<service>:<category>/<test>` (e.g. `cda:core_query_mechanics/discovery`);
`--query` also accepts the bare `<category>/<test>` or just the leaf slug (`discovery`).

## Anatomy of a test

### `test.md` — the prompt

```markdown
---
name: "Discovery + value casing (`vital_status`)"
description: This tests the column_values → filter loop on a column the examples never touch.
---
Using CDA, how many human subjects are recorded as deceased? Show me how you confirmed the value you filtered on.
```

`name` and `description` are metadata for humans and reports. **Everything after the closing
`---` is the prompt**, passed to the agent verbatim.

### `rationale.md` — the design rationale (humans only)

```markdown
# Intended Behavior
The agent inspects `column_values('vital_status')` to confirm the lowercase `dead`, then filters
`summarize_subjects(match_all=['vital_status = dead', 'species = human'])` to reach ≈ 8,556 subjects.

# Incorrect Behavior
The agent guesses `Deceased`/`DEAD` without checking, or looks for vital status on the `subject`
table when it actually lives on `observation`.
```

### `eval.yaml` — the machine-gradeable checks

```yaml
checks:
  - number: {name: deceased_subjects, target: 8556, tolerance_percent: 15}
  - behavior: called column_values('vital_status') to confirm 'dead' before filtering
  - substring_any: [dead, deceased]
```

> ### ⚠️ `rationale.md` is design rationale — not an input
>
> It exists to explain **why the checks in `eval.yaml` are what they are**: the correct method
> and the trap a weak agent falls into. It is the reasoning you use to *design* the checks,
> written down so the next author understands the intent.
>
> **The harness never reads it.** The parser
> ([`harness/parsing.py`](../harness/parsing.py)) loads *only* `eval.yaml`. `rationale.md` is
> never parsed, never reaches the agent, never reaches the judge, and plays no part in grading.
> **If a behavior should affect the score, it must be encoded as a check in `eval.yaml`** —
> putting it in `rationale.md` does nothing.

## Exactly what gets passed, at every point

```
test.md ─frontmatter─→ (reports only)
        └─prompt──────→ AGENT  ┐
SKILL.md ──────────────→ AGENT  ├─→ final answer ─→ DETERMINISTIC checks (string/number match)
skill file paths ──────→ AGENT  ┘                └→ JUDGE LLM (behavior / count_at_least)
eval.yaml ─────────────────────────────────────────→ grader (defines the checks)
rationale.md (# Intended / # Incorrect Behavior) ───→ (nothing — humans only)
```

### 1 · To the agent under test
Per test, `harness/runner.py:run_query` builds two messages via `harness/skills.py`:

**System prompt** — fixed for every test (`build_system_prompt` → `_HARNESS_ROLE`):
> You are an autonomous data-analysis agent with a Python execution tool. You are given an
> Agent Skill describing how to query a specific NCI Cancer Research Data Commons
> repository. Follow the skill precisely… Execute real code against the live API to obtain
> real values — never fabricate numbers, IDs, or results. If the task is outside the
> repository's scope, say so and redirect… Finish with a clear final answer that states the
> key numbers, IDs, and conclusions explicitly.

**User message** (`build_user_message(service, prompt)`):
```
## Agent Skill: <skill name>

<skill>
<the ENTIRE SKILL.md for the mapped skill>     # full text, inlined
</skill>

### Skill reference files (read on demand from your Python tool)
These live on disk under:
  <absolute skill dir>
Read any with, e.g.: print(open(".../references/ENDPOINTS.md").read())
Available files:
  - references/ENDPOINTS.md      # PATHS ONLY — contents are NOT inlined;
  - examples/…                   #   the agent opens the files itself via run_python
  …

---

## Task
<the test.md prompt, verbatim>
```

**Tools** — exactly one: `run_python` ([`harness/llm/tools.py`](../harness/llm/tools.py)).
It executes Python in a namespace that **persists across calls** and returns the combined
stdout/stderr, clipped to 20,000 chars per call. The agent runs a ReAct loop
([`harness/llm/agent.py`](../harness/llm/agent.py)): model turn → optional `run_python`
call(s) → tool output fed back as the next message → … until the model replies with **plain
text and no tool call** (that text is the **final answer**) or it hits `--max-steps`.

The agent is given **only**: the system role, the full skill text, the reference-file *paths*,
and the prompt. It never sees `eval.yaml` or `rationale.md`, nor the test's `name`/`description`.

### 2 · Grading the final answer (deterministic, no LLM)
`harness/checks.py` matches these against the **final-answer string only**:

| check | how it's decided against the final answer |
|-------|-------------------------------------------|
| `substring` | the (case-insensitive) string appears |
| `substring_any` / `substring_all` | at least one / every listed string appears |
| `must_not_contain` | none of the listed strings appear (encodes the trap's wrong answer) |
| `regex` | the pattern matches somewhere in the answer |
| `number` | some number parsed from the answer is within `target ± tolerance` |
| `set_contains` | every listed member appears |

### 3 · To the judge LLM (semantic checks only)
`behavior` and `count_at_least` are graded by `--judge-model` via
[`harness/judge.py`](../harness/judge.py) — one `complete()` call each, **no tools**.

**System prompt** — a fixed strict grader returning `{"pass": bool, "reason": "<=30 words"}`:
> You are a strict, literal grader… decide whether ONE assertion about an AI agent's run is
> satisfied, using only the agent's final answer and its code/tool trace as evidence. Be
> conservative: if the evidence does not clearly support the assertion, it FAILS…

**User message** — depends on the check type:

| check | what the judge receives |
|-------|-------------------------|
| `behavior` | the check's assertion text + the task prompt + the **transcript** (final answer **and** every step's code with clipped stdout — the whole thing clipped to 18,000 chars) |
| `count_at_least` | the check's assertion text + the task prompt + the **final answer only** (clipped to 12,000 chars) |

The judge sees the assertion, the prompt, and the answer/transcript — and **nothing else**
(no `description`, `name`, or `rationale.md`). Under `--no-judge` these checks are left *unscored*.

A test passes when every **scored** check passes (deterministic always score; semantic score
only when the judge runs).

## Authoring `eval.yaml`

The file is a top-level `checks:` list. Each list item is a single-key map keyed by the check
type — scalar for simple checks, an inline list for the multi-string ones, a nested map for the rest:

```yaml
checks:
  - substring: "Cisplatin"
  - substring_any: [dead, deceased]          # also substring_all, must_not_contain
  - regex: 'PDC\d{6}'                         # or {name: ids, pattern: 'PDC\d{6}'}
  - number: {name: deceased_subjects, target: 8556, tolerance_percent: 15}
  #   tolerances: tolerance_percent | tolerance_absolute | tolerance_pp | exact: true
  - set_contains: {name: top_genes, members: [TP53, CDKN2A]}
  - count_at_least: {name: projects, min: 10}   # judged
  - behavior: used case_filters for the cohort, not filters   # judged
```

Guidance:
- Encode the **trap** as `must_not_contain` (the wrong number, the hallucinated capability).
- `number` grades by tolerance, never exact equality — counts drift with data releases.
- `behavior` is the workhorse for *method* assertions (which endpoint / filter slot / the
  decline-and-redirect); write it as one decidable claim, since the judge reads it literally.
- Anything you wrote in `rationale.md` that should affect the score must also appear here as a
  check — that prose is not graded.
