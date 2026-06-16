# GC (General Commons) skill — live-harness evaluation queries

Five natural-language tasks for evaluating the `general-commons` (GC, formerly CDS) skill in a live
agent harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into, and
has a machine-gradeable outcome.

**These are not the skill's examples.** They deliberately avoid the entities the `examples/` use — the
pancreatic/PDAC CPTAC proteomics file set (`phs001287`, JHU TMT11 `.gct`), the Glioblastoma faceted
cohort, and the KF-ESGR Ewing-sarcoma discovery study (`phs001228`) — so a passing run demonstrates the
skill *generalizes* rather than pattern-matching the worked examples.

**Endpoint:** `https://general.datacommons.cancer.gov/v1/graphql/` — a single GraphQL endpoint (the
**trailing slash matters**). A GET returns the schema; POST a `{"query": "..."}` body for real work (no
`variables` key needed). **Auth:** none — all GC metadata/search is open-access. The API returns
**metadata only; it never downloads data bytes.**

**Verified live on 2026-06-11**, GraphQL schema `3.1.0`, data model `11.0.4`, data release `12.0.0`
("2026 May Released GC data"): **9 programs, 89 studies, 120,867 subjects, 109,535 samples, 615,790
files**. `programList`: CCDI 16, TCIA-RADIOLOGY 35, DCCPS 20, Kids First 7, PDXNet 4, HTAN 2, CPTAC 1,
MP2PRT 1, NCIcaNano 1.

**Counts drift with each data release** — `number` checks below grade order-of-magnitude / tolerance,
not exact equality. Re-baseline against the metrics queries (`numberOfStudies` / `numberOfSubjects` /
the per-study `*Count` queries) if a value has shifted.

Things every query exercises (the GC footguns): GC returns **HTTP 200 even on errors** — inspect
`errors`. **`first` defaults to 10** — set it or silently get 10 rows (max 10000). **Every scalar comes
back as a String** — counts and `file_size` too, so cast before arithmetic/comparison. Most per-study
queries **require `phs_accession`** (omitting it is a hard error, not an empty result), so resolve it
first via `studies`/`programs`. In the faceted layer each facet bucket's count field is **`subjects`,
not `count`** (`GroupCount { group subjects }`).

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap, e.g. a promised signed URL).
- `regex` — a pattern the answer (or an ID it returns) must match, e.g. the DRS shape `dg\.4DFC/[0-9a-f-]+`.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for small integers); large counts grade to order-of-magnitude / ~15–20%.
- `set_contains` — the answer's enumerated set must include these members (superset check), e.g. discovered `phs_accession`s.
- `count_at_least` — number of distinct items returned is ≥ N (e.g. studies in a cohort).
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (e.g. cast `file_size` to int; passed `phs_accession`; used `subjects` not `count`).

**Drift caveat:** all counts/IDs were live-verified on **2026-06-11** against GC data release `12.0.0`
(schema `3.1.0`, model `11.0.4`) and move with each data release. `number` checks therefore grade
order-of-magnitude / tolerance, **not** exact equality — re-baseline against the metrics queries
(`numberOfStudies` / `numberOfSubjects` / per-study `*Count`) and the faceted `subjectCountBy*` buckets
if a value has shifted. The *behaviors* being graded (routing, the non-`phs` key, String-cast,
`subjects`-not-`count`, DRS/no-direct-download) are stable.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|:--:|:--:|:--:|:--:|:--:|
| Routing / GC-is-a-fallback boundary | ✓ | | | | |
| GC-only data (caNanoLab / nanotech) | | ✓ | | | |
| Non-`phs` study key (`10.17917` DOI quirk) | | ✓ | | | |
| `phs_accession` resolution (required arg) | ✓ | ✓ | ✓ | | ✓ |
| Default-10 pagination footgun | | | ✓ | ✓ | |
| String-cast scalars (counts / `file_size`) | | | ✓ | | ✓ |
| Faceted search (`searchSubjects` + `GroupCount.subjects`) | ✓ | | | ✓ | |
| Facet-bucket-counts-records quirk (bucket ≠ distinct subjects) | ✓ | | | ✓ | |
| Files / DRS `file_id` / `drs_uri` / no direct download | | | | | ✓ |
| Controlled access / dbGaP / CGC manifest | ✓ | | | | ✓ |
| Open-access / no-auth metadata model | ✓ | ✓ | ✓ | ✓ | ✓ |
| "Don't invent fields" (schema is fixed) | ✓ | | | ✓ | ✓ |
