# CTDC skill — live-harness evaluation queries

Five natural-language tasks for evaluating the `clinical-translational-data-commons` skill in a live
agent harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into, and
has a machine-gradeable outcome.

**Endpoint:** `https://clinical.datacommons.cancer.gov/v1/graphql/` (trailing slash) — a **single
GraphQL endpoint, POST-only**. There is no REST API and no GET.
**Auth:** none. All CTDC metadata/search is open-access. The API serves metadata only; file *bytes* are
fetched out-of-band via CRDC DRS / the Cancer Genomics Cloud.
**Request-body quirk:** the JSON body **MUST include a `variables` key** (even `{}`). Omitting it is a
hard error (HTTP 400, `Cannot invoke "java.util.Map.keySet()" because "variables" is null`) — *not* an
empty result. Sibling Bento commons don't require this.
**Errors:** GraphQL query errors come back **HTTP 200 with an `errors` array** (the variables error is
the exception — it 400s); always inspect `errors`.

**Data verified:** CTDC currently holds **1 study — CMB ("CM Biobank"), 248 participants, 1,140
specimens, 2,033 files, 42 targeted therapies**. Ground-truth values were confirmed against the live
API on **2026-06-11**. CTDC is early/small and counts will drift as the study set grows — re-verify
against `searchParticipants` (the live "totals" call) if numbers shift; the *behaviors* being graded
are stable.

The `requests` package is not installed in this harness; the verification used `python3` +
`urllib.request`. The skill's worked examples use `requests` — either library is acceptable as long as
the body carries the `variables` key.

> These queries deliberately use entities that appear **nowhere** in the skill's `examples/`:
> the examples work Plasma Cell Myeloma, Non-Small Cell Lung Carcinoma + Osimertinib, and Melanoma +
> Nivolumab/Pembrolizumab/Dabrafenib (participant MSB-00205), and download DICOM/Radiology-Imaging
> files. These tests use **Colorectal Carcinoma**, **Bevacizumab/Panitumumab**, **carcinogen
> exposure**, and **Variant Call Files (vcf)** instead — a passing run demonstrates the skill
> *generalizes*, not pattern-matches.

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (this is how the trap's wrong answer is encoded).
- `regex` — a pattern the answer (or an ID it returns) must match, e.g. the DRS shape
  `(?i)dg\.4DFC/<uuid>`.
- `number` — a named numeric value with a tolerance (`±N` absolute for small integers, `±N%` for
  counts, `±N pp` for percentages).
- `set_contains` — the answer's enumerated set must include these members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace, not just
  prose (e.g. used `subjects` not `count`; paged past `first: 10`; parsed the bracketed string; included
  the `variables` key).

**Drift caveat:** all counts/IDs were live-verified on **2026-06-11** against CTDC's single GraphQL
endpoint, and move as the (currently single-study, 248-participant) commons grows. `number` checks
therefore grade **order-of-magnitude / tolerance, not exact equality** — re-baseline against
`searchParticipants` (the live totals + facet-counts call) if a value has shifted. The graded
**behaviors** (POST + `variables` key, `GroupCount.subjects`, controlled-vocab discovery, bracketed-
string parsing, per-specimen-vs-per-participant counting, DRS-based download) are stable across releases.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|:--:|:--:|:--:|:--:|:--:|
| POST-only + required `variables` key + HTTP-200/400 errors | ✓ | | | | |
| `searchParticipants` totals (live "numberOf*") | ✓ | ✓ | | | ✓ |
| `GroupCount.subjects` not `count` | ✓ | ✓ | ✓ | | ✓ |
| Cohort build by `ctep_disease_term` + filter facet counts | | ✓ | | ✓ | |
| Controlled-vocabulary exact strings (wrong value → empty, not error) | | ✓ | ✓ | | |
| Carcinogen-exposure facet (clinical/translational-distinctive) | | | ✓ | | |
| `participantOverview` rows + paging past `first: 10` | | | | ✓ | |
| Bracketed-string array quirk (parse, don't index) | | | | ✓ | |
| Specimen/file counts per-specimen/per-file ≠ per-participant | | | | | ✓ |
| File DRS id (`dg.4DFC/<uuid>`) + DRS/CGC download, no API bytes | | | | | ✓ |
| Open-access / no-auth model | ✓ | ✓ | ✓ | ✓ | ✓ |
