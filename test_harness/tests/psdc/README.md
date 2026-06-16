# PS-DC skill — live-harness evaluation queries

Five natural-language tasks for evaluating the `population-sciences-data-commons` (PS-DC) skill in a
live agent harness. Each targets a high-value capability, embeds a trap a skill-less agent falls into,
and has a gradeable outcome.

**Endpoint:** `https://populationsciences.datacommons.cancer.gov/v1/graphql/` (trailing slash) — a
**single GraphQL endpoint, POST-only**. No REST.
**Auth:** none — PS-DC metadata/search is open-access (no key, token, or login).
**Request rules:** the body **must** include a `variables` key (even `{}`) — omitting it is a hard
error (`Cannot invoke "java.util.Map.keySet()" because "variables" is null`, observed as HTTP 400, body
still carries the `errors` key). A GET is rejected (HTTP 405, `"API will only accept POST requests"`).
GraphQL query errors otherwise come back **HTTP 200** with an `errors` array — always inspect it. Use
`urllib.request` (the `requests` package is not installed in the harness).

**Data state (verified 2026-06-11):** PS-DC is a **new, undocumented prototype** holding **3 studies**:
NLST (National Lung Screening Trial, Clinical Trial, **48,860**), PLCO (Prostate, Lung, Colorectal and
Ovarian Cancer Screening Trial, Cohort Study – Prospective, **151,383**), and PBCS (Polish Breast
Cancer Study, Case-Control Study, **4,886**).

**Defining behavior of this prototype:** only **study-level, Elasticsearch-backed** queries work today.
Verified working: `globalStatsBar`, `searchStudies`, `tabStudy`, `studyDemographics`,
`primarySiteMorphology`, `dataCollectionPage`, `studyGeneral`, `studyFiles`, `minMaxBoundQuery`. The
**participant-, sample-, file-record-, and node-level queries currently ERROR** with
`Unable to connect to localhost:7687, ensure the database is running...` (their Neo4j backend is
unreachable). Re-verified live on 2026-06-11: `subjectInfo`, `fileOverview`, `diagnosis`,
`schemaVersion`, and node queries all return that error. An agent must treat that message as "endpoint
not live yet," not a query mistake, and must not fabricate the requested rows.

Counts may drift with future prototype loads — re-verify the working queries above if numbers shift;
the *behaviors* being graded are stable. The urllib helper used for all ground truth below:

```python
import urllib.request, json
URL = "https://populationsciences.datacommons.cancer.gov/v1/graphql/"
def psdc(query):
    body = {"query": query, "variables": {}}          # the "variables" key is REQUIRED
    r = urllib.request.Request(URL, data=json.dumps(body).encode(),
                               headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(r, timeout=90) as resp:
        out = json.loads(resp.read().decode())
    if out.get("errors"):                              # HTTP 200 even on query errors
        raise RuntimeError(out["errors"])
    return out["data"]
```

---

## Automated grading

Each per-query **Checks** bullet is one objectively decidable assertion, tagged with a check type:

- `substring` / `substring_any` / `substring_all` — case-insensitive substring(s) that must appear in
  the agent's final answer (`_any` = at least one; `_all` = every one).
- `must_not_contain` — substring(s) that must NOT appear (encodes the trap, e.g. a fabricated participant row).
- `regex` — a pattern the answer (or an ID it returns) must match, e.g. the DRS shape
  `drs://nci-crdc\.datacommons\.io/dg\.4DFC/[0-9a-f-]+` or a dbGaP `phs\d{6}` accession.
- `number` — a named numeric value with a tolerance (`±N%` for counts, `±N` absolute for small
  integers). Grades order-of-magnitude / within-tolerance, not exact equality.
- `set_contains` — the answer's enumerated set must include the listed members (superset check).
- `count_at_least` — the number of distinct items returned is ≥ N.
- `behavior` — an assertion about METHOD, checkable from the agent's emitted code / tool trace (e.g.
  selected `{ group subjects }` rather than a scalar; reported an endpoint as not-live instead of
  fabricating rows; read `subjects` as a study count).

**Drift caveat:** all counts/IDs are live-verified on **2026-06-11** against the PS-DC GraphQL endpoint
and move with each prototype data load, so `number` checks grade order-of-magnitude / tolerance (not
exact equality) — re-baseline against the working study-level queries (`globalStatsBar`,
`studyDemographics`, `searchStudies`, `studyFiles`) if a value has shifted. The graded **behaviors**
(POST + `variables` key; `subjects` not `count`; `subjects`-means-studies in facets; treating
`Unable to connect to localhost:7687` as not-live; not fabricating participant rows; DRS-id handoff) are
stable across loads.

---

## Coverage summary

| Skill surface | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|:--:|:--:|:--:|:--:|:--:|
| `studyDemographics` (age/sex/race) + `{ group subjects }` subselection | ✓ | | | | |
| `variables`-key / POST-only request rules | ✓ | | | | |
| Participant/record endpoints are NOT live (Neo4j down) — no fabrication | | ✓ | | | |
| dbGaP handoff via `dbgap_accession_id` | | ✓ | | | ✓ |
| `primarySiteMorphology` real field names (`group`/`group_code`/`subjects`) | | | ✓ | | |
| `searchStudies` facets + `subjects`-means-STUDIES caveat | | | | ✓ | |
| `studyFiles` + CRDC DRS id (`drs://…/dg.4DFC/…`) | | | | | ✓ |
| Study-level-only / metadata-only model (no participant bytes) | | ✓ | | | ✓ |
| Open-access / no-auth | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fresh study targets (PLCO / PBCS, not the NLST examples) | ✓ | ✓ | ✓ | ✓ | ✓ |
