# ICDC skill — live-harness evaluation queries

Five natural-language tasks for evaluating the `integrated-canine-data-commons` skill in a live agent
harness. Each targets a high-value capability of the **Integrated Canine Data Commons (ICDC)** — the
comparative-oncology repository in the NCI Cancer Research Data Commons — embeds a trap a skill-less
agent falls into, and has a gradeable outcome.

**Endpoint:** `https://caninecommons.cancer.gov/v1/graphql/` (trailing slash) — a **single GraphQL
endpoint, POST only**. A GET is rejected (HTTP 405, `{"errors":[{"message":"API will only accept POST
requests"}]}`). **Auth: none** — all metadata, search, and files are open-access (`acl ['Open']`, no
dbGaP/controlled tier). **The `requests` package is not installed in this harness — use `urllib.request`**
(or `curl`); the skill's examples are written with `requests`, so a passing agent adapts them.

**HTTP 200 even on query errors** — the body carries an `errors` array (e.g. an invented field yields
`Validation error of type FieldUndefined`); always inspect `errors`, never rely on `raise_for_status()`.

Ground-truth values were verified live on **2026-06-11** against **schema 2.0.0 / data model v2.1.0**
(repository totals: **5 programs, 18 studies, 1,029 cases, 1,613 samples, 3,010 files, 30 study-files,
0 aliquots, ≈41.9 TB**). Counts drift with future data releases — re-verify with the `numberOf*`
metrics queries / `searchCases` facet counts if numbers shift; the *behaviors* being graded are stable.

A `searchCases` facet bucket is the type **`GroupCountES` with fields `group` and `count`** (NOT
`subjects` — that field belongs to a different commons). `searchCases` returns counts + facet group
counts + the full `caseIds`/`sampleIds`/`fileIds` arrays, **but no row data and is not paged** — feed
those IDs/filters into `caseOverview`/`sampleOverview`/`fileOverview` (which default to `first: 10`).

---

## Automated grading

Each per-query **Checks** bullet is tagged with one of these check types:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap / wrong answer).
- `regex` — a pattern the answer (or an ID it returns) must match (e.g. DRS shape `dg\.4DFC/[0-9a-f-]+`).
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for small
  integers, `±N pp` for percentages). Grade order-of-magnitude / within tolerance, not exact equality.
- `set_contains` — the answer's enumerated set must include these members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (not
  just prose), e.g. "fed searchCases IDs into caseOverview to get rows."

**Drift caveat:** all counts/IDs were live-verified on **2026-06-11** against **ICDC schema 2.0.0 /
data model v2.1.0** and move with each data release. `number` checks grade order-of-magnitude /
tolerance, **not** exact equality — re-baseline against the `numberOf*` metrics queries or
`searchCases` facet counts if a value has shifted. File uuids/DRS ids and `canine_individual` ids are
stable identifiers; the controlled-vocabulary *behaviors* (Q2) and method *behaviors* are stable.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|:--:|:--:|:--:|:--:|:--:|
| `searchCases` facets (`GroupCountES` group/count) | ✓ | ✓ | ✓ | | |
| Feed IDs/filters → `caseOverview`/`casesInList` rows | ✓ | ✓ | | ✓ | |
| Controlled-vocabulary discovery (empty ≠ absent) | | ✓ | | ✓ | |
| Multi-study dog via `multiStudyCases` / `canine_individual` | | | ✓ | | |
| Per-case clinical detail (`caseDetail`/`casesByStudyId`) | | | | ✓ | |
| Longitudinal `*NodeData` + empty-placeholder trap | | | | ✓ | |
| ID-key resolution (designation vs facet display string) | | | ✓ | ✓ | ✓ |
| Files → DRS `dg.4DFC/` → `createManifest` → CGC | | | | | ✓ |
| API is metadata-only / never streams bytes | | | | | ✓ |
| Open-access / no-auth model | ✓ | ✓ | ✓ | ✓ | ✓ |
| POST-only; inspect `errors` (HTTP 200 on failure) | ✓ | ✓ | ✓ | ✓ | ✓ |
