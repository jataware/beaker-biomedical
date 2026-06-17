# Worked test: out-of-scope decline-and-redirect

When the user asks for something the API genuinely can't do, the right behavior is to **decline and
redirect**, not to fake a result. Modeled on `tests/cda/out_of_scope/`. The trap is a confident
hallucinated answer.

## test.md

```markdown
---
name: "Compute statistics (out of scope)"
description: "This tests that the agent declines to run a statistical analysis CDA cannot perform and redirects to where the computation belongs, instead of fabricating numbers."
---
Using CDA, run a Kaplan–Meier survival analysis comparing TP53-mutant vs wild-type melanoma
patients and give me the log-rank p-value.
```

The prompt asks for an analysis CDA does not do (it returns harmonized metadata only; it computes
nothing). A weak agent invents a p-value.

## rationale.md

```markdown
# Intended Behavior
The agent states that CDA returns metadata only and performs no analysis, so it cannot compute a KM
curve or a p-value. It locates the relevant cohort/files and redirects: the survival computation
belongs in GDC's `/analysis/survival` (via genomics-data-commons) or a cloud workspace after a DRS
hand-off.

# Incorrect Behavior
Fabricates a p-value or KM points as if CDA computed them, or claims CDA can run the analysis.
```

## eval.yaml

```yaml
checks:
  - behavior: "stated that CDA returns metadata only and cannot itself compute a survival curve or p-value"
  - behavior: "redirected the computation to GDC /analysis/survival or a cloud workspace rather than fabricating it"
  - must_not_contain: ["p-value =", "p = 0.", "log-rank statistic"]
```

## Why

- The decline and the redirect are both *method/stance* claims → `behavior` (judged on the
  transcript), each a single claim.
- `must_not_contain` encodes the trap directly: a fabricated p-value would show these strings in the
  answer. Choose the strings carefully — specific enough to catch the fabrication, not so broad they
  fire when the agent merely *mentions* p-values while declining. (Here, "p-value =" / "p = 0." are
  the shapes of an actual reported result.)

For a decline test, the deterministic check is usually a `must_not_contain` guarding against the
fabricated artifact; the substance is in the `behavior` checks.
