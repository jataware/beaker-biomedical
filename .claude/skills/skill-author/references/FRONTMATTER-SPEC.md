# SKILL.md frontmatter spec

The YAML block between the opening and closing `---` at the top of `SKILL.md`. Load this when
writing or fixing frontmatter. Full spec: https://agentskills.io/specification

## Fields

| Field | Required | Constraints |
|---|---|---|
| `name` | yes | 1–64 chars, lowercase `a-z`/`0-9`/`-` only. No leading/trailing/consecutive hyphens. **Must equal the directory name.** |
| `description` | yes | 1–1024 chars. What it does + when to use it + trigger keywords. The only field loaded every session — see BEST-PRACTICES.md. |
| `compatibility` | no | 1–500 chars. Runtime needs: packages, services, API keys (by env-var name). |
| `metadata` | no | Arbitrary string key/value map (e.g. `author`, `source-uuid`). |
| `license` | no | License name or reference to a bundled file. |
| `allowed-tools` | no | Space-separated pre-approved tool names (experimental). |

## Shape

```yaml
---
name: genomic-data-commons
description: >-
  Query, search, and download cancer genomics data from the NCI GDC REST API. Use when the user
  needs cases/files in TCGA, TARGET, CPTAC…, somatic-mutation/CNV metadata, gene-expression
  matrices, survival data, or DTT manifests; or ad-hoc GraphQL against the GDC schema.
compatibility: Python 3 with the `requests` package. No API key for open data; controlled-access downloads need GDC_TOKEN.
metadata:
  author: integrations
---
```

Use a YAML block scalar (`>-`) for a multi-line `description` so it stays one logical string.

## Rules that bite

- **`name` must match the directory exactly.** A mismatch means the skill won't resolve. The
  validator checks this.
- **`description` is a hard 1024-char ceiling** and is what gets the skill activated — every
  wasted word there is a word not spent on a trigger keyword.
- **`compatibility` is for real requirements only.** Name the package and the env-var
  (`Requires GDC_TOKEN`), don't editorialize. Omit the field entirely if there are no special needs.
- The body below the closing `---` has no format requirements — but follow the house structure
  (intro, base URL/auth, Critical rules, endpoint table, Gotchas, pointers).
