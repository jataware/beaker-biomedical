# Worked: a failing harness check → a minimal skill edit

The full loop on a single failing test, using the GDC mutation-frequency denominator gap as the case.

## 1. Signal

```bash
cd test_harness
python -m harness.cli run --query gdc:query_mechanics/mutation_frequency_denominator \
    --model claude-sonnet-4-6 --detail -o report.json
```

Output: the `number` check (TP53 frequency in TCGA-ACC ≈ 16.67%) **fails** — the answer says 0.08%.
A `behavior` check ("computed the cohort frequency using `case_filters` for the denominator") also
fails.

## 2. Read the trace and diagnose

In `report.json`, the `code_trace` shows the agent called `/analysis/top_mutated_genes` passing the
cohort as `filters`. The result *looked* fine (a small percentage, no error) — a silent
plausible-wrong-answer. Cause: **skill gap.** The skill explains the endpoint but never says the
denominator comes from `case_filters`; the agent had no way to know.

This is not a model limitation (nothing in the skill steered it right) and not a bad test (16.67% is
the live-verified correct value).

## 3. Locate the fix

Cross-cutting and silent-failure-class → a **Critical rule** in `SKILL.md`, with the detail in the
existing `references/MUTATION-FREQUENCY.md`. Not a new example; not inline detail.

## 4. Edit (minimal, verified)

Confirm both numbers live first, then add to `SKILL.md` Critical rules:

```markdown
- **Mutation-frequency denominators come from `case_filters`, not `filters`.** Pass the cohort as
  `case_filters`; `filters` only restricts which mutations are *ranked*, leaving the denominator at
  the GDC-wide total and collapsing the frequency to nonsense (TP53 in TCGA-ACC reads 0.08% via
  `filters` vs the correct 16.67% via `case_filters`). Never divide a cohort numerator by
  `num_gdc_ssm_cases`. See [references/MUTATION-FREQUENCY.md](references/MUTATION-FREQUENCY.md).
```

## 5. Re-verify

```bash
python -m harness.cli run --query gdc:query_mechanics/mutation_frequency_denominator \
    --model claude-sonnet-4-6 --detail
```

Both checks now pass. Re-run the rest of `--service gdc` to confirm the new rule didn't perturb a
sibling (it shouldn't — it's additive and scoped to the analysis endpoints). Run the failing test
2–3× to confirm the fix is stable, not a lucky sample.
