# CDA skill — generalization test queries

Validation prompts for the `cancer-data-aggregator` skill. **These are not examples** — they
deliberately use diseases, genes, projects, columns, IDs, and modalities that appear **nowhere** in
`examples/` or `references/`, so a passing run demonstrates the skill *generalizes* rather than
pattern-matching the worked examples.

## Automated grading

Each check in a test's `# Automated Checks` block is one objectively decidable assertion, tagged with a
check type (shared across all suites; see `test_harness/README.md`):

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap's wrong answer / a fabricated
  value or capability).
- `regex` — a pattern the answer (or a returned ID) must match.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for small
  integers). Grade order-of-magnitude / within tolerance, **not** exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted `cdapython` code / tool
  trace (which table/column, the `column_values → filter` loop, the hand-off key, the decline/redirect),
  not just prose. For CDA the `behavior` checks carry most of the signal — the discover→filter loop, the
  metadata-only boundary, and the correct downstream commons are what distinguish a generalizing run.

**Drift caveat:** counts were verified live (~June 2026) and move with each CDA data release, so
`number` checks grade order-of-magnitude / tolerance, not exact equality — re-baseline against
`release_metadata` if a value has shifted. The graded **behaviors** (discover→filter, correct
table/column, hand-off keys, metadata-only boundary, decline/redirect) are stable across releases.

---

## Scoring rubric

- **Pass (generalizes):** A1–A6 use the discover→filter loop with correct tables/values and land within
  ~10% of the verified counts; B1–B2 route to the right commons; C1–C3 perform the CDA locate, name the
  correct hand-off key/commons, and issue a sensible downstream query; D1–D6 decline/redirect without
  fabricating.
- **Sharpest signals:** **A5** (wildcards an unseen free-text diagnosis instead of returning 0), **A2/A4**
  (uses the `treatment`/ICDC corners), **C1** (frequencies from GDC, not CDA's mutation table; doesn't
  default to TCGA), and the **D** set (knows CDA's metadata-only boundary). If those hold on these
  unfamiliar subjects, the skill is generalizing, not echoing the examples.
- Counts drift with releases — re-verify against `release_metadata` before treating a mismatch as a miss.
