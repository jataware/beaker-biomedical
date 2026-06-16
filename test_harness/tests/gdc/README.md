# GDC skill — live-harness evaluation queries

Natural-language tasks for evaluating the `genomic-data-commons` (GDC) skill in a live agent harness.
Each targets a high-value capability, embeds a trap a skill-less agent falls into, and has a
machine-gradeable outcome. Ground truth was verified against the live REST API
(`https://api.gdc.cancer.gov`) on **2026-06-11**, against **Data Release 45.0 (2025-12-04)** (confirmed
via `GET /status`). The API is fully open-access — none of these queries need a token. The harness has
Python but **no `requests` package**; the agent should use `urllib.request` and POST
`application/json`.

Counts drift with each data release — re-verify against `/status` + a `facets`/`/analysis` re-run if a
number has shifted. The *behaviors* being graded (right endpoint, right filter slot, right
interpretation) are stable; `number` checks grade tolerance/order-of-magnitude, not exact equality.

These queries deliberately avoid the entities used in the skill's own `examples/` (breast / TCGA-BRCA,
ER status, leukemia discovery, BRCA1 BAM slicing, MYC, kidney's VHL/PBRM1 top-mutated worked example).
A passing run must show the skill *generalizes*, not pattern-matches the worked examples.

---

## Automated grading

Each per-query **Checks** bullet is tagged with one check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap's wrong answer).
- `regex` — a pattern the answer (or a returned ID) must match.
- `number` — a named numeric value with tolerance: `±N%` (counts), `±N` (small integers), `±N pp`
  (percentage points). Counts grade order-of-magnitude / within tolerance, not exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (which
  endpoint, which filter slot, which interpretation), not just prose.

**Drift caveat:** all `number` values were live-verified on **2026-06-11** against **GDC Data Release
45.0**, and they move with each data release. Grade `number` checks by tolerance/order-of-magnitude,
not exact equality; re-baseline against `GET /status` plus a fresh `facets` / `/analysis` re-run if a
value has shifted. The graded *behaviors* (correct endpoint, correct filter slot, correct
interpretation, inspecting `warnings`) are stable across releases.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 | Q6 |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| Project discovery (don't default to TCGA) | ✓ | | | | | |
| Value/vocabulary casing (`disease_type` lowercase) | ✓ | | | | | |
| Mutation freq: `case_filters` vs `filters` denominator | | ✓ | | | | |
| Cancer Gene Census default + mandatory notice | | ✓ | | | | |
| "Highly expressed" = most variable (`gene_selection`) | | | ✓ | | | |
| Survival: array-of-filters log-rank vs single curve | | | | ✓ | | |
| Statistical interpretation (p≈0.37 not significant) | | | | ✓ | | |
| Facet-name validity + `warnings` inspection | | | | | ✓ | |
| `files.access` open vs controlled / no-auth model | | | | | | ✓ |
