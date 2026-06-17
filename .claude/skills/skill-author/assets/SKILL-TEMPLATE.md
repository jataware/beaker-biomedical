---
name: <skill-directory-name>
description: >-
  <What it does — lead with action verbs.> Use when <trigger conditions + the domain keywords a
  user would type>. <When NOT to use it / which sibling skill to prefer.>
compatibility: <Runtime needs: packages, services, API keys by env-var name. Omit this field if none.>
metadata:
  author: <author>
---

# <Service name>

<One sentence: what this API is and what it's for.>

**Base URL:** `<https://…>`

## Authentication

<Open vs credential-gated operations. Which work anonymously; which need a token and how it's passed.>

## Critical rules

<The cross-cutting facts that silently produce wrong answers if missed — each stated as a
procedure with a verified number. These lines justify the skill.>

- **<rule>** — <the procedure + why it matters>.

## Endpoint catalogue

| Endpoint | Returns | Notes |
|---|---|---|
| `<path>` | <what> | <gotcha / default> |

## Filter / query syntax

<The minimal shape, one example. Push the full operator/field tables to references/.>

## Gotchas

- **<local trap>** — <what goes wrong and the fix>.

## Example usage

<The single smallest useful inline example.>

For complete worked recipes see [examples/](examples/):
- [<task>.md](examples/<task>.md) — <one line>.

## References

- [references/<TOPIC>.md](references/<TOPIC>.md) — <what it covers>. Load when <trigger>.

Upstream specs are preserved verbatim in [assets/](assets/).
