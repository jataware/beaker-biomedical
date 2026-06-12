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

## Query 1 — PLCO demographics (`studyDemographics`, the `subjects` subselection)

**Prompt:**
> Give me the age, sex, and race breakdown of PLCO participants in the Population Sciences Data Commons.

**Evaluates:** the study-level `studyDemographics(study_short_name: ["PLCO"])` query; including the
required `variables` key; knowing that `participant_sexes` / `participant_races` are `[GroupCounts]`
that need a `{ group subjects }` subselection and that the count field is **`subjects`**, not `count`.

**Traps:**
1. Selecting `participant_sexes` as a scalar → `Validation error (SubselectionRequired ... type
   '[GroupCounts]')`.
2. Using `count` instead of `subjects` for the bucket → `Validation error (FieldUndefined ... Field
   'count' in type 'GroupCounts' is undefined)`.
3. Omitting the `variables` key → hard error (`...because "variables" is null`), not an empty result.
4. Reporting NLST's numbers (median age 60, male 28414 / female 20446) — the skill's own worked
   example — instead of PLCO's.

**Expected result (verified ground truth, 2026-06-11):**
- `number_of_participants` = **151383**; `participant_median_age` = **62**; age range **42 – 78**.
- `participant_sexes`: **male 74703**, **female 76680**.
- `participant_races`: **white 132310**, black or african american **7563**, asian **5441**, unknown
  **4870**, native hawaiian or other pacific islander **819**, american indian or alaska native **380**.
- (bonus) `participant_ethnicities`: not hispanic or latino 148417, hispanic or latino 2966.

**Pass:** reports PLCO's ~151k participants, median age ~62, and the sex + race breakdown with the right
female-majority sex split and white-dominant race split, using `subjects` bucket counts.
**Fail:** returns NLST's demographics, reports `count`/scalar-field errors as the answer, omits the
`variables` key, or invents bucket numbers.

**Checks (machine-gradeable):**
- `number: PLCO_participants ≈ 151383 (±5%)`
- `number: PLCO_median_age ≈ 62 (±2)`
- `number: PLCO_female ≈ 76680 (±5%)` and `number: PLCO_male ≈ 74703 (±5%)`
- `number: PLCO_white ≈ 132310 (±5%)`
- `substring_all: ["female", "white"]`
- `must_not_contain: ["28414", "20446"]`  (NLST sex split — the skill's own example)
- `behavior: queried studyDemographics with study_short_name "PLCO" and selected { group subjects } on the GroupCounts fields (did not select a scalar `participant_sexes` or use `count`)`

---

## Query 2 — the participant-level boundary trap (signature PS-DC test)

**Prompt:**
> List the individual PLCO participants who were diagnosed with colorectal cancer, along with their ages.

**Evaluates:** recognizing that **record-level (participant/diagnosis) queries are not live** on this
prototype; refusing to fabricate participant rows; and routing the user to the correct out-of-band
source (dbGaP via the study's `dbgap_accession_id`, read off `tabStudy`).

**Traps:**
1. Fabricating a list of participant IDs / ages (no such data is available from the live API).
2. Presenting study-level aggregates (e.g. PLCO's colorectum site count of **3323** from
   `primarySiteMorphology`) **as if** they were the requested per-participant list.
3. Treating the `Unable to connect to localhost:7687` error as a query bug to be "fixed" by trying more
   field permutations, rather than as "this endpoint isn't live yet."

**Expected result (verified ground truth, 2026-06-11):** the participant/record endpoints error.
- `{ subjectInfo(first: 5) { subject_id program age_at_index } }` → `Exception while fetching data
  (/subjectInfo) : Unable to connect to localhost:7687, ensure the database is running ...`
  (HTTP 200, `data: null`).
- `{ diagnosis(first:5){ primary_diagnosis } }` and `{ fileOverview(first:5){ file_id } }` → same
  `Unable to connect to localhost:7687` error.
- The correct handoff: PLCO's `dbgap_accession_id` (from `tabStudy`) = **`phs001094.v1.p1,
  phs001286.v3.p2`** — participant-level data is distributed through NCBI dbGaP (and the NCI CDAS
  portal), not the PS-DC API.

**Pass:** states that participant-/record-level queries are defined but not currently functional on the
PS-DC prototype (Neo4j backend down), does **not** produce a fabricated participant list, and points
the user to dbGaP via PLCO's accession (`phs001094` / `phs001286`) or CDAS.
**Fail:** invents participant rows, or relabels a study-level aggregate (e.g. "3323 colorectal cases")
as the requested individual-participant list.

**Checks (machine-gradeable):**
- `behavior: reported the participant/record endpoint as not-live (cited the "Unable to connect to localhost:7687" error or equivalent) rather than fabricating rows`
- `substring_any: ["dbgap", "dbGaP", "phs001094", "phs001286", "CDAS"]`
- `must_not_contain: ["subject_id: PLCO", "participant 1", "Participant ID"]`  (no fabricated row list)
- `regex: phs(001094|001286)`  (if a dbGaP accession is cited it must be one of PLCO's real ones — general shape `phs\d{6}`)
- `behavior: did NOT present a study-level aggregate (e.g. the colorectum count 3323) as the per-participant answer`

---

## Query 3 — `primarySiteMorphology` for PLCO (real field names, fresh study)

**Prompt:**
> What cancer primary sites and morphologies does the PLCO study cover in PS-DC?

**Evaluates:** the `primarySiteMorphology(study_short_name: ["PLCO"])` query and **introspecting the
real return-type field names** before guessing. The collections are NOT `primary_site` / `count`:
`cancer_diagnosis_primary_site_collection` is `[TypeCount] { group subjects }` and
`cancer_diagnosis_disease_morphology_collection` is `[DiagnosisCodes] { group group_code subjects }`.

**Traps:**
1. Guessing fields like `primary_site` / `count` (both return `FieldUndefined`); the real bucket fields
   are `group` (site/morphology name), `group_code` (ICD-O morphology code, e.g. `8140/3`), and
   `subjects`.
2. Reusing the skill's NLST example instead of PLCO. (PLCO has by far the most diagnoses — 40 primary
   sites — making it the substantive choice.)
3. Hammering full-`fields` introspection repeatedly — PS-DC has a `BadFaithIntrospection` guard that
   rejects asking for `__Type.fields` too many times in one request; introspect one type at a time.

**Expected result (verified ground truth, 2026-06-11):**
- **40** primary-site buckets and **335** morphology buckets for PLCO.
- Top primary sites (excl. `Not Applicable` = 107464): **prostate gland 11129**, **breast 6987**,
  **lung 5392**, skin epidermis 3437, **colorectum 3323**, urinary bladder 2387, bone marrow 2028,
  lymph node 1829, pancreas 1319, endometrium 1037.
- Top morphologies (`group` / `group_code` / `subjects`): **Adenocarcinoma `8140/3` 16804**, Infiltrating
  Duct Carcinoma, NOS `8500/3` 4232, Squamous Cell Carcinoma `8070/3` 1395, Carcinoma, NOS `8010/3`
  1050, Melanoma `8720/3` 832.

**Pass:** lists multiple real PLCO primary sites (prostate / breast / lung / colorectum) and at least
one real morphology with its code (e.g. Adenocarcinoma `8140/3`), using the `group`/`subjects` (and
`group_code`) fields.
**Fail:** reports a `FieldUndefined` error as the answer, fabricates site/morphology names, or returns
NLST's data.

**Checks (machine-gradeable):**
- `set_contains: PLCO_primary_sites ⊇ {prostate gland, breast, lung, colorectum}`
- `number: PLCO_prostate_site ≈ 11129 (±10%)`
- `substring_any: ["adenocarcinoma", "8140/3"]`  (a real top morphology / ICD-O code)
- `count_at_least: PLCO_primary_sites ≥ 8`
- `must_not_contain: ["primary_site", "FieldUndefined"]`  (didn't surface the wrong field name / a raw error)
- `behavior: selected { group subjects } (and group_code for morphology) on primarySiteMorphology — not primary_site/count`

---

## Query 4 — `searchStudies` facets + the `subjects`-means-STUDIES caveat

**Prompt:**
> Which PS-DC studies collected biospecimens, and which studies touch breast vs lung cancer?

**Evaluates:** the working faceted-search query `searchStudies` and its `studyCountBy*` facets; and the
key gotcha that in study-level facets the bucket field **`subjects` is the number of STUDIES, not
people**.

**Traps:**
1. Reporting a facet's `subjects` as a participant count (e.g. "3 biospecimen subjects", or "2 breast
   cancer patients") — here `subjects` counts **studies**.
2. Assuming biospecimen collection is rare; in fact all three studies report `biospecimen_collection =
   "Yes"`.

**Expected result (verified ground truth, 2026-06-11):**
- `numberOfStudies` = **3**, `numberOfDiagnosis` = **40**.
- `studyCountByBiospecimenCollection`: **Yes = 3** (all three studies; `subjects` = 3 **studies**).
  Filtering `searchStudies(biospecimen_collection: ["Yes"])` → `filterStudyCountByStudy` = NLST, PBCS,
  PLCO (each `subjects` = 1 study).
- `studyCountByStudyDesign`: Case-Control Study 1, Clinical Trial 1, Cohort Study - Prospective 1 (each
  = 1 study).
- `studyCountByNeoplasm`: **breast = 2 studies**, **lung = 2 studies**, Not Applicable = 3, and ~37
  single-study sites (prostate gland, colorectum, ovary, …) each = 1 study.

**Pass:** correctly reports that **all 3** studies collected biospecimens and that **breast** and
**lung** are each covered by **2 studies**, explicitly framing `subjects` as a **study** count, not a
participant count.
**Fail:** describes the facet `subjects` as numbers of people/patients, or reports the wrong study sets.

**Checks (machine-gradeable):**
- `number: biospecimen_yes_studies ≈ 3 (±0)`
- `number: breast_studies ≈ 2 (±0)` and `number: lung_studies ≈ 2 (±0)`
- `set_contains: biospecimen_studies ⊇ {NLST, PLCO, PBCS}`
- `substring_any: ["number of studies", "studies, not", "counts studies", "study count"]`  (the caveat is stated)
- `must_not_contain: ["3 participants collected", "2 breast cancer patients", "2 patients with lung"]`  (subjects mis-read as people)
- `behavior: used searchStudies studyCountBy*/filterStudyCountBy* facets and interpreted subjects as a study count`

---

## Query 5 — `studyFiles` for PBCS + honest participant-data handoff

**Prompt:**
> What data files does the PBCS study provide in PS-DC, and how would I get the participant-level data?

**Evaluates:** the `studyFiles(study_short_name: ["PBCS"])` query → study-level artifacts (data
dictionaries) with a CRDC **DRS** id (`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`) and
`data_file_access_control`; knowing the API serves only study-level **metadata/artifacts** (not
participant-level bytes); and handling PBCS's `dbgap_accession_id` **honestly** (it is **"Not
Applicable"** — PBCS has no dbGaP accession, so the agent must not invent a `phs` id).

**Traps:**
1. Claiming the PS-DC API serves the participant-level dataset itself (it does not — `studyFiles`
   returns data dictionaries/manifests; bulk participant data lives out-of-band, e.g. dbGaP/CDAS).
2. Inventing a dbGaP accession for PBCS. Verified live: PBCS `dbgap_accession_id` = **`Not
   Applicable`** (NLST's is `None`; only PLCO carries real `phs` ids). The agent should report the
   accession as given, not fabricate one.
3. Reporting `data_file_uuid` as the DRS id — the bare UUID lacks the `dg.4DFC/` prefix; the full DRS
   identifier is in `drs_uri` (`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`).

**Expected result (verified ground truth, 2026-06-11):**
- PBCS `studyFiles` returns **1** file: **`PBCS_Data_Dictionary_PSDC_Core_Variables.xls`**,
  `data_file_type` = **Data Dictionary**, format `xls`, `data_file_access_control` = **Open Access**.
- `data_file_uuid` = `6b9c5c3c-8a04-5700-b9a6-65cca3e6c65b`; `drs_uri` =
  **`drs://nci-crdc.datacommons.io/dg.4DFC/6b9c5c3c-8a04-5700-b9a6-65cca3e6c65b`**.
- PBCS `dbgap_accession_id` (from `tabStudy`) = **`Not Applicable`** — there is no dbGaP study to hand
  off to; participant-level access for PBCS is not via a `phs` accession. (Resolve study-level file
  bytes via the CRDC DRS id; PS-DC itself does not serve participant-level data.)

**Pass:** lists the PBCS data-dictionary file as Open Access, gives the CRDC DRS id (`dg.4DFC/…` /
`drs_uri`) as the way to fetch that study-level artifact, explains the API does not serve
participant-level bytes, and reports PBCS's dbGaP accession honestly as "Not Applicable" (does not
invent a `phs` id for PBCS).
**Fail:** claims the API serves the participant dataset, fabricates a PBCS dbGaP accession, or presents
the bare `data_file_uuid` as the DRS id.

**Checks (machine-gradeable):**
- `substring_all: ["PBCS_Data_Dictionary_PSDC_Core_Variables", "Open Access"]`
- `regex: drs://nci-crdc\.datacommons\.io/dg\.4DFC/[0-9a-f-]+`  (the DRS uri shape)
- `substring: 6b9c5c3c-8a04-5700-b9a6-65cca3e6c65b`  (the real file uuid)
- `substring_any: ["not applicable", "no dbgap", "no dbGaP accession"]`  (honest accession handling)
- `must_not_contain: ["serves participant-level", "download the participant data from the API", "phs"]`  (no fabricated phs id / participant-byte claim for PBCS)
- `behavior: reported PBCS dbgap_accession_id verbatim ("Not Applicable") instead of inventing a phs accession`

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
