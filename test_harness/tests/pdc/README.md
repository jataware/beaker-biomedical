# PDC skill — live-harness evaluation queries

Three natural-language tasks for evaluating the `proteomic-data-commons` skill in a live agent
harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into, and has a
gradeable outcome. Ground-truth values were verified against the live API (`https://proteomic.datacommons.cancer.gov/graphql`)
on 2026-06-05 (PDC Data Release 6.1; ~9 programs / 30 projects / 227 studies / 6,239 cases / 195,269
files). Counts may drift with future data releases — re-verify against `getPDCMetrics` if numbers
shift; the *behaviors* being graded are stable.

---

## Automated grading

Each check in a test's `# Automated Checks` block is one objectively decidable assertion, tagged with a
check type (shared across all suites; see `test_harness/README.md`):

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap, e.g. "absolute abundance").
- `regex` — a pattern the answer (or a returned ID) must match, e.g. a `pdc_study_id` `PDC\d{6}`.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for log2 ratios /
  small integers). Grade order-of-magnitude / within tolerance, **not** exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (the
  discovery query, the version resolution, dropping QC channels by `sample_type`, the md5 check, the
  transient-null retry), not just prose.

**Drift caveat:** counts/IDs were live-verified on **2026-06-05** against **PDC Data Release 6.1**
(`https://proteomic.datacommons.cancer.gov/graphql`) and move with each data release, so `number`
checks grade order-of-magnitude / tolerance, not exact equality — re-baseline with `getPDCMetrics` if a
value has shifted. Version-specific UUIDs (e.g. the `study_id` above) are stable identifiers; the graded
**behaviors** (discovery-not-hardcode, relative-not-absolute interpretation, version resolution, QC
filtering, md5 verification, transient-null retry) are stable across releases.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 |
|---|:--:|:--:|:--:|
| Discovery (disease → studies) | ✓ | | |
| Three study-ID flavors / version resolution | | ✓ | ✓ |
| `quantDataMatrix` + relative-not-absolute interpretation | | ✓ | |
| Aliquot → case mapping (`biospecimenPerStudy`) + QC filtering | | ✓ | |
| Files / `signedUrl` / download / expiry | | | ✓ |
| Open-access / no-auth model | ✓ | ✓ | ✓ |
| Transient-null retry / robustness | | | ✓ |
