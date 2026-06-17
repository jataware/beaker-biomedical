# Worked: the agent took the trap → an anti-pattern rule

A `must_not_contain` check firing means the agent produced exactly the wrong answer the test guards
against. The fix is usually to call the trap out *by name* as an anti-pattern.

## 1. Signal

```bash
python -m harness.cli run --query gdc:query_mechanics/project_discovery \
    --model claude-sonnet-4-6 --detail
```

The `must_not_contain: ["only TCGA-BRCA", "1098 breast"]` check fails: asked for breast-cancer data,
the agent scoped straight to `TCGA-BRCA` and reported its 1098 cases as the answer.

## 2. Diagnose

Read the trace: the agent assumed "breast cancer = TCGA-BRCA" and never enumerated the other
projects. Cause: **skill gap** — the skill describes how to query a project but doesn't warn against
the default-to-TCGA reflex, and breast actually spans ~20 projects.

(Confirm it's a gap, not a bad test: the test is right — TCGA-BRCA alone *is* the wrong answer here.
And it's not a pure model limit: the skill gave no signal to do otherwise.)

## 3. & 4. Locate + edit

The trap is cross-cutting (it applies to every disease/site query) → a **Critical rule** stated as
an explicit anti-pattern, plus the discover-first recipe in an example. Verify the project count live
first:

```markdown
- **Don't default to TCGA — discover the project set first.** A disease or anatomical site spans
  many projects (breast → ~20, not just TCGA-BRCA; TARGET-AML has >10× the leukemia cases of
  TCGA-LAML). When the user names a cancer type rather than a `project_id`, facet `/cases` by
  `project.project_id` and filter on the full set. See
  [examples/discover_projects_for_disease.md](examples/discover_projects_for_disease.md).
```

## 5. Re-verify

Re-run the query: the agent now enumerates the projects and the `must_not_contain` passes (and any
`count_at_least`/`set_contains` on the project set should pass too). Run sibling tests — an
anti-pattern rule is additive and low-risk, but confirm it didn't make the agent over-enumerate on a
query where the user *did* name a single project.

## Note

When a `must_not_contain` fires, always re-check it isn't a **bad test** — that the forbidden string
isn't something a *correct* answer would legitimately contain in passing. Here, "only TCGA-BRCA" as
the scope is unambiguously the wrong answer, so the test is sound and the skill is what needs the fix.
