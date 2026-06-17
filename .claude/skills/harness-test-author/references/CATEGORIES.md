# Placement: service, category, leaf, ref

How to decide where a test lives and what it's called. Load this in step 1.

## Service → skill

`<service>` is the top directory under `tests/` and selects the skill loaded for the test
(`harness/config.py:SERVICE_TO_SKILL`):

| service | skill under `skills/` |
|---|---|
| `gdc`  | genomics-data-commons |
| `pdc`  | proteomic-data-commons |
| `cda`  | cancer-data-aggregator |
| `gc`   | general-commons |
| `icdc` | integrated-canine-data-commons |
| `ctdc` | clinical-translational-data-commons |
| `psdc` | population-sciences-data-commons |

## Category — reuse the taxonomy, extend only when needed

`<category>` is a descriptive grouping (a directory). Prefer an existing one; add a new one only for
a genuinely new theme. The taxonomy in use today:

- **`query_mechanics`** (and CDA's richer `core_query_mechanics`) — the bulk: discovery, counting,
  filtering, facets, value-casing, the per-API quirks. Most tests are here.
- **`file_handoff`** — the "find the files, hand off a DRS id / manifest, do **not** download" case
  each suite has.
- Boundary categories, one per kind of scope edge:
  - `out_of_scope` (cda) — the API can't do this; decline and redirect.
  - `routing_boundary` (gc) — "is this even the right commons?"
  - `participant_boundary` (psdc) — participant/sample-level asks that the prototype can't answer.
  - `access_model` (gdc) — open vs controlled access.
  - `file_modality` (cda) — imaging→IDC, proteomics→PDC modality routing.
  - `round_trips` (cda) — multi-step cross-repository round trips.

If you're adding a normal query test, it's almost certainly `query_mechanics`. If it's a "the agent
should *refuse* / *redirect*" test, use (or mirror) the relevant boundary category.

## Leaf slug and ref

The leaf directory is a short, meaningful slug for the specific thing under test:
`mutation_frequency_denominator`, `facet_name_hallucination`, `discovery`,
`controlled_vocab_empty_trap`. Name it for the behavior, not "test3".

The test's **ref** (for `--query`) is `<service>:<category>/<test>`, e.g.
`gdc:query_mechanics/mutation_frequency_denominator`. `--query` matching is forgiving: the full ref,
the bare `<category>/<test>`, or just the leaf slug all select it — so keep leaf slugs unique enough
to be unambiguous on their own.
