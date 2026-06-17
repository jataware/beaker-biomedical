# Structuring a skill: what goes where, and how to split

Load this when deciding the file layout, or when a `SKILL.md` has grown too long and needs
breaking apart.

## The directory

```
<skill-name>/
├── SKILL.md          # required: frontmatter + terse instructions (loaded on activation)
├── auth.yaml         # required here: credential declaration (see AUTH.md)
├── references/       # detailed docs, loaded on demand
├── examples/         # one worked, runnable recipe per file, loaded on demand
├── assets/           # upstream specs / data files, preserved verbatim
└── scripts/          # code the agent imports and runs as-is (optional)
```

`references/` and `examples/` aren't in the bare spec but are the established convention in this
repo — keep them.

## The routing table

| Content | Destination | Why |
|---|---|---|
| Critical rules, base URL, auth mechanism, the gotchas, an endpoint summary table | `SKILL.md` body | The agent needs these on every invocation |
| Full parameter/field catalogues, operator tables, per-topic deep dives | `references/<TOPIC>.md` | Large, consulted occasionally, named by topic |
| A complete worked task (probe → query → result), runnable | `examples/<task>.md` | A pattern to adapt, not re-derive |
| OpenAPI/Swagger, GraphQL SDL, man pages, schema dumps | `assets/<file>` | Source of truth, preserved verbatim, never edited |
| A function the agent must call unchanged | `scripts/<name>.py` | Code to import, not a pattern to copy |

Rule of thumb: if the source content is small (a one-screen API with a handful of endpoints),
most of it can live in `SKILL.md`. The moment a table is longer than the rules around it, or a
recipe needs more than a short fenced block, move it out and leave a one-line pointer with a
load-trigger.

## examples/ are patterns, not scripts

An `examples/*.md` file is reference material the agent reads and *adapts* when writing novel code.
Each is a `# Title`, a sentence on what it demonstrates, and one fenced code block that actually
runs. Name them for the task (`discover_projects_for_disease.md`), never `example-1.md`. Code the
agent must call *verbatim* is different — that goes in `scripts/` as a real `.py` file.

## Breaking a monolith into references + examples

When a `SKILL.md` (or a draft, or an upstream doc dump) is too long, refactor it in place rather
than trimming content:

1. **Read the whole thing and tag each block** by role: *critical rule*, *reference detail*,
   *worked recipe*, *verbatim spec*, or *general knowledge the model already has*.
2. **Delete the general-knowledge blocks.** (How REST works, what JSON is, generic retry advice.)
3. **Lift each reference-detail block** into `references/<TOPIC>.md` grouped by topic
   (`FILTERS.md`, `FIELDS.md`, `FACETS.md`…). Leave behind, in `SKILL.md`, a one-line summary plus
   a pointer with the load-trigger.
4. **Lift each worked recipe** into `examples/<task>.md` — one task per file. In `SKILL.md`, keep
   only the smallest useful inline example, then list the rest under a `## Example usage` /
   `## References` section.
5. **Move verbatim specs** to `assets/` and link them from the references that explain them.
6. **What survives in `SKILL.md`** is: the intro, base URL + auth, the **Critical rules**, one
   endpoint/usage table, the **Gotchas**, and the pointers. If that's still long, the rules
   themselves are probably too verbose — tighten each to one decision.

The test: a reader of `SKILL.md` alone should know *what the API is, what will silently go wrong,
and which file to open for any given task* — and nothing more.

See [examples/split_monolith_into_examples.md](../examples/split_monolith_into_examples.md) for a
worked before/after.
