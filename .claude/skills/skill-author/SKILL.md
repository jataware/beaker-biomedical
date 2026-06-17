---
name: skill-author
description: >-
  Author a new Agent Skill (agentskills.io format) with progressive disclosure — a terse
  SKILL.md plus references/, examples/, assets/, and scripts/. Use when creating a skill from
  upstream docs, an OpenAPI/GraphQL spec, a live API, or a described workflow, especially a new
  NCI CRDC / biomedical data-commons skill under skills/. Verify content against the real source,
  don't transcribe docs. To fix an existing skill from live feedback use skill-improver; to write
  evaluation tests use harness-test-author.
compatibility: Python 3 with pyyaml for the validator script. Network access to probe the live source API.
metadata:
  author: jataware
---

# Authoring an Agent Skill

An Agent Skill is a directory of instructions an agent loads to operate one API or workflow.
The entire craft is **progressive disclosure**: put the least in front of the model that it
needs, and let it pull the rest on demand.

- **Metadata** (`name` + `description`) — loaded for *every* skill, every session (~100 tokens).
  The description alone decides whether the skill activates, so make it earn that.
- **`SKILL.md` body** — loaded when the skill activates. Keep it terse (aim ≤ ~200 lines):
  base URL, auth, the critical rules, a usage/endpoint table, the gotchas. Nothing the model
  already knows.
- **`references/`, `examples/`, `assets/`, `scripts/`** — loaded only when the model opens
  them. Tables, field catalogues, worked recipes, and verbatim specs live here, not in `SKILL.md`.

> Write for a capable model. Add what it **lacks** — gotchas, real field names, the non-obvious
> sequence — and omit what it **knows** (how HTTP, JSON, pagination, or auth headers work in
> general). A long `SKILL.md` is a bug, not thoroughness. See [references/STRUCTURE.md](references/STRUCTURE.md).

## Procedure

1. **Pick the source and a sibling to model on.** Find the closest existing skill and match its
   shape — REST/Python → like `skills/genomics-data-commons`; GraphQL/Bento → like
   `skills/general-commons` or `skills/proteomic-data-commons`. Cross-skill consistency is a feature.

2. **Probe the live source — do not trust the docs.** Confirm the production base URL, the real
   field/value names, casing, representative counts, and error behavior *before* writing guidance.
   Surprises become critical rules. See [references/LIVE-VERIFICATION.md](references/LIVE-VERIFICATION.md).

3. **Draft a terse `SKILL.md`.** Frontmatter per [references/FRONTMATTER-SPEC.md](references/FRONTMATTER-SPEC.md);
   body = one-line intro, base URL, auth, **Critical rules**, an endpoint/usage table, **Gotchas**,
   and a pointer to each reference/example that says *when* to load it. Start from
   [assets/SKILL-TEMPLATE.md](assets/SKILL-TEMPLATE.md).

4. **Push detail out of `SKILL.md`.** Parameter/field catalogues and long topic detail →
   `references/*.md`. Worked, runnable recipes → `examples/*.md`, one per task. Upstream specs
   (OpenAPI, GraphQL SDL, man pages) → `assets/` verbatim. Do-not-modify code the agent imports
   and runs → `scripts/`. The routing table and the splitting method are in
   [references/STRUCTURE.md](references/STRUCTURE.md).

5. **Write `auth.yaml`.** Declare credentials, or `credentials: []` for an open metadata API.
   See [references/AUTH.md](references/AUTH.md).

6. **Validate.** Run `python scripts/validate_skill.py <skill-dir>`: frontmatter parses, `name`
   matches the directory, `description` ≤ 1024 chars, `SKILL.md` within budget, every internal
   link resolves, `auth.yaml` parses, no empty subdirectories. Then grep every backticked field
   or identifier against the live catalogue — invent nothing.

## What goes where

| Content | Destination |
|---|---|
| Critical rules, base URL + auth, the gotchas, endpoint summary | `SKILL.md` body |
| Parameter/field tables, schemas, long per-topic detail | `references/<TOPIC>.md` |
| Worked end-to-end recipes, one task each | `examples/<task>.md` |
| Upstream specs, preserved verbatim | `assets/` |
| Code the agent imports and runs as-is | `scripts/` |

For the deeper guidance load: [references/BEST-PRACTICES.md](references/BEST-PRACTICES.md)
(description optimization, content strategy, calibrating control, routing) and
[references/STRUCTURE.md](references/STRUCTURE.md) (splitting a monolith into references + examples).

When a skill is *already* live and you're fixing it from observed failures rather than writing it
fresh, that's the **skill-improver** skill, not this one.
