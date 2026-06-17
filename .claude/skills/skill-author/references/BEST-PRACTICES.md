# Skill-authoring best practices

The judgement calls behind a good skill. Load this while drafting `SKILL.md` or deciding how
prescriptive to be.

## The one rule everything follows: add what the model lacks

A skill is not documentation. The model already knows HTTP, JSON, pandas, pagination, retries,
and how an Authorization header works. Do not re-teach any of it. A skill earns its tokens by
supplying what the model *cannot* guess:

- The **real** field names, value casing, and base URL (verified live — see LIVE-VERIFICATION.md).
- The **non-obvious sequence** (e.g. "discover the projects first, then filter on the full set").
- The **gotchas** — silent defaults, traps, denominators, fields that 200 on an invalid value.
- The **scope boundary** — what this API can't do and where to redirect instead.

If a sentence would be true of any REST API, cut it.

## Description optimization (the highest-leverage 1024 characters)

The `description` is the *only* part loaded for every skill, every session, and it alone decides
activation. Write it as: **what it does** (lead with action verbs) + **when to use it** (the
trigger conditions and the domain keywords a user would actually type).

- Bad: "Helps with genomics data."
- Good: "Query, search, and download cancer genomics data from the NCI GDC REST API. Use when the
  user needs cases/files in TCGA, TARGET, CPTAC…, somatic-mutation or copy-number metadata, gene
  expression matrices, survival data, or DTT manifests."

Pack it with the nouns that distinguish *this* skill from its siblings, and state when **not** to
use it (defer to the more specific skill) so overlapping skills don't all fire at once.

## Content strategy

- **Gotchas are the highest-value content.** A single "this facet returns 200 with no aggregations
  on an invalid field name" line saves the agent an entire failed investigation. Mine them from
  the source and from your own live probing, and put them where the agent will see them.
- **Provide a default, not a menu.** Pick the one right tool/endpoint/pattern and lead with it;
  mention alternatives in a clause, not a decision tree. "Use POST for non-trivial searches" beats
  "you could use GET or POST depending on…".
- **Procedures over declarations.** "Facet `/cases` by `project.project_id`, then filter on the
  bucket keys" is actionable; "the project field is important" is not.
- **State numbers you verified.** Real counts ("22,638→716") make a rule credible and let the
  agent sanity-check its own output. Mark them as live-verified and dated where it matters.

## Calibrating control: prescriptive vs free

Match the leash to the fragility of the operation.

- **Be prescriptive** where a wrong move silently produces a *plausible* wrong answer: exact filter
  slots, the denominator that comes from `case_filters` not `filters`, the mandatory default cut,
  the precise endpoint. Spell out the exact call. These are the lines that justify the skill.
- **Give freedom** where the task is genuinely open: analysis approach, output formatting, how to
  summarize. Don't over-script what the model does well.
- **Preserve every CRITICAL/IMPORTANT directive** from the source verbatim in intent — never soften
  a "you must" into a "you may".

## Routing and "when to use"

In a family of related skills (the CRDC commons are the model case), every skill must say where it
sits relative to its siblings — in the `description` and a short "when to use this vs X" note. For a
low-priority or overlapping skill, say so plainly and defer to the more specific one. The goal is
that exactly the right skill activates, not all of them.

## Tell the agent *when* to load each file

A pointer that only says a file exists wastes the disclosure model. Say the trigger.

- Good: "Read `references/FACETS.md` when constructing a `facets=` query, or after one comes back
  with no aggregations."
- Bad: "See `references/` for more."

Every reference and example linked from `SKILL.md` should carry its load-trigger. If you can't name
a trigger, the content probably belongs inline — or doesn't belong at all.

## Anti-patterns

- A `SKILL.md` that runs past a few hundred lines, or repeats a reference table inline.
- Teaching general programming or restating the OpenAPI spec prose.
- Inventing field names from the docs without confirming them live.
- A pile of `examples/` that are really one example with the parameters changed — collapse them.
- Menus of equivalent options with no recommended default.
