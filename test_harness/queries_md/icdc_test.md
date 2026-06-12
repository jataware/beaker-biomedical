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

## Query 1 — Faceted cohort for a non-osteosarcoma disease (bladder cancer)

**Prompt:**
> How many ICDC cases are bladder cancer, and what breeds, studies, and disease sites do they span?
> List some of the actual cases.

**Evaluates:** the cohort-building workflow — `searchCases` to read the facet landscape and the
post-filter facet sub-counts (`filterCaseCountBy*`), then an `*Overview` query to list real rows.
Tests that the agent does not assume a single study and reads `GroupCountES.count` correctly.

**Traps:**
1. `searchCases` returns **no row data** — the agent must call `caseOverview` (or `casesInList` with
   the `caseIds`) to actually *list* cases. Stopping at `searchCases` answers "how many" but not "list."
2. Reading `subjects` instead of `count` from the `GroupCountES` buckets (that field doesn't exist
   here → a `FieldUndefined` error or empty parse).
3. Hardcoding one study (e.g. "UBC01"). The bladder cohort spans **5 studies**, and two of them are
   *not* dedicated bladder studies (TCL01, ORGANOIDS01).

**Expected result (verified ground truth):**
- **116 Bladder Cancer cases** (`searchCases(diagnosis: ["Bladder Cancer"])` → `numberOfCases` 116,
  `numberOfSamples` 162, `numberOfFiles` 341, across **5 studies**).
- **Studies** (`filterCaseCountByStudyCode`): **UBC02 56, UBC01 34, UBC03 16, TCL01 7, ORGANOIDS01 3**.
- **Top breeds** (`filterCaseCountByBreed`): **Scottish Terrier 42, Mixed Breed 21, Beagle 11**,
  Labrador Retriever 5, … (≈29 distinct breeds).
- **Disease sites** (`filterCaseCountByDiseaseSite`): **Bladder 51, "Bladder, Urethra" 41**,
  "Bladder, Urethra, Prostate" 10, "Bladder, Prostate" 5, … (note the multi-site compound values).
- Real case rows from `caseOverview(diagnosis: ["Bladder Cancer"], first: …)` — e.g.
  `ORGANOIDS01-OR-A`, `TCL01-Bliley`, `UBC03-800-425`, `UBC01-776-675-Vm20`. `caseOverview` with
  `first: 200` returns all **116** rows.

**Pass:** reports ≈116 cases, names the multi-study span (≥3 studies, not one), gives breed and
disease-site breakdowns from the facets, and lists actual case_ids via an `*Overview`/`casesInList`.
**Fail:** reports only a count with no rows, claims one study, uses `subjects`, or invents case_ids.

**Checks (machine-gradeable):**
- `number: bladder_cases ≈ 116 (±15%)`
- `number: bladder_studies ≈ 5 (±1)` — the cohort spans about five studies, not one.
- `substring_all: ["Scottish Terrier", "Bladder"]` — the dominant breed and a real disease-site value appear.
- `set_contains: studies ⊇ {UBC02, UBC01}` (a strong answer also surfaces UBC03 / TCL01 / ORGANOIDS01).
- `count_at_least: listed_case_ids ≥ 3` — actual case_ids are enumerated, not just a count.
- `regex: case_id matches (UBC0[123]-|TCL01-|ORGANOIDS01-)\S+` — at least one listed id is a real ICDC bladder case_id.
- `behavior: fed searchCases counts/IDs into caseOverview (or casesInList) to produce rows` (did not stop at searchCases).
- `must_not_contain: ["subjects"]` (as the facet-count field name; the field is `count`).

---

## Query 2 — Controlled-vocabulary empty-result trap ("Urinary Bladder")

**Prompt:**
> Build me a cohort of ICDC cases whose disease site is "Urinary Bladder."

**Evaluates:** that the agent treats facet/filter values as **controlled vocabularies** and discovers
the valid values rather than trusting a plausible-sounding guess. ICDC has no disease-site value
"Urinary Bladder"; the real values are `Bladder`, `Bladder, Urethra`, etc.

**Trap:** `searchCases(disease_site: ["Urinary Bladder"])` returns **0 cases with NO `errors` key** (an
empty list is *not* an error). A skill-less agent concludes "ICDC has no bladder data" — which is
flatly wrong (Q1 shows 116 bladder cases). The agent must read `caseCountByDiseaseSite` to find the
real strings and re-run with one of them.

**Expected result (verified ground truth):**
- `searchCases(disease_site: ["Urinary Bladder"])` → `numberOfCases 0`, `caseIds []`, and the response
  has **no `errors`** (HTTP 200, clean empty). `caseOverview(disease_site: ["Urinary Bladder"])` → `[]`.
- The valid `caseCountByDiseaseSite` values include: **`Bladder` (51)**, **`Bladder, Urethra` (41)**,
  `Bladder, Urethra, Prostate` (10), `Bladder, Prostate` (5), `Bladder, Urethra, Vagina` (3),
  `Urethra, Prostate` (2), `Distal Urethra` (1), `Urethra` (1) — there is **no** "Urinary Bladder".
- Re-running with the real value: `searchCases(disease_site: ["Bladder"])` → **51 cases**.
- The agent should also note that *diagnosis* "Bladder Cancer" (116 cases, Q1) is the broader handle if
  the user wants all bladder-cancer cases regardless of the compound site string.

**Pass:** detects the empty result, explicitly attributes it to a wrong controlled-vocabulary value
(not absent data), discovers the real `disease_site` values, and rebuilds a non-empty cohort (≈51 for
`Bladder`, or 116 via the `Bladder Cancer` diagnosis).
**Fail:** reports "ICDC has no bladder cases / no data," treats the empty list as a hard error, or never
discovers the valid facet values.

**Checks (machine-gradeable):**
- `number: urinary_bladder_cases == 0` — the literal "Urinary Bladder" value yields zero.
- `substring_any: ["Bladder, Urethra", '"Bladder"', "Bladder (51", "51 cases"]` — surfaces a real disease-site value/count.
- `behavior: read caseCountByDiseaseSite to enumerate valid disease_site values before reconcluding`
- `behavior: re-ran the query with a valid value and returned a non-empty cohort (≈51 Bladder, or 116 via diagnosis)`
- `must_not_contain: ["no bladder data", "ICDC does not have", "no such cases exist", "ICDC has no bladder"]` — the empty result must not be reported as absent data.

---

## Query 3 — Map one dog across multiple studies

**Prompt:**
> Find an ICDC dog that took part in more than one study, and list its cases and samples across those
> studies.

**Evaluates:** ICDC's distinctive `canine_individual` linkage — the same physical dog appears as a
separate `case_id` in each study. Tests `searchCases(study_participation: ["Multiple Study"])` to find
the multi-study cases, then `multiStudyCases(case_id)` (or the `canine_individual` node) to pool one
dog's cases/samples/files. **18 of the 1,029 cases participate in multiple studies.**

**Trap:** treating each `case_id` as a distinct animal (so the dog's data looks like two unrelated
patients), or never resolving the shared `canine_individual_id`. A skill-less agent also tends to grab
the worked-example dog; a generalizing agent finds a fresh one.

**Expected result (verified ground truth):**
- `searchCases(study_participation: ["Multiple Study"])` → **18 caseIds**, including the UBC01/UBC02
  bladder-cancer pairs and the OSA01/NCATS-COP01 pairs.
- A clean fresh example — **canine individual `0003`** (a male **Scottish Terrier** with **Bladder
  Cancer**): `multiStudyCases(case_id: "UBC01-776-675-Vm20")` →
  `individualId "0003"`, `caseIds ["UBC02-776-675-63", "UBC01-776-675-Vm20"]`, **3 sampleIds**
  (`UBC02-776-675-63-S1`, `UBC01-776-675-Vm20-c`, `UBC01-776-675-Vm20-b`), **6 fileIds**.
- The two cases span two studies: **UBC01** ("Antitumor Activity … Vemurafenib in Dogs with BRAF-mutant
  Bladder Cancer") and **UBC02** ("Basal and Luminal Molecular Subtypes in … Canine Urothelial
  Carcinoma"). The `canine_individual(canine_individual_id: "0003") { cases { case_id study {
  clinical_study_designation } } }` node traversal confirms both.
- *(Any of the other 17 multi-study cases is acceptable as long as the answer ties ≥2 case_ids spanning
  ≥2 studies to one `canine_individual`. Avoid individualId "0009" — that's the skill's worked example.)*

**Pass:** identifies one dog with ≥2 case_ids across ≥2 distinct studies under a single
`canine_individual_id`, and pools its samples/files. Names the real ids.
**Fail:** treats the two case_ids as separate dogs, fails to find the shared individual, or reuses the
example dog "0009" without finding a fresh one.

**Checks (machine-gradeable):**
- `count_at_least: studies_for_dog ≥ 2` — the chosen dog spans at least two distinct studies.
- `count_at_least: case_ids_for_dog ≥ 2` — at least two case_ids tied to the same individual.
- `regex: individual_id matches \b0\d{3}\b` — a real loader-generated `canine_individual_id` (e.g. 0003).
- `substring_any: ["UBC01", "UBC02"]` (for the 0003 path) — names the studies the dog participated in.
- `behavior: resolved a shared canine_individual via multiStudyCases or the canine_individual node` (did not treat the case_ids as unrelated patients).
- `must_not_contain: ["0009"]` — must use a fresh individual, not the skill's worked example.

---

## Query 4 — Per-study clinical detail, and the empty longitudinal-node trap

**Prompt:**
> Pull the clinical detail for the UBC01 vemurafenib bladder-cancer trial — the per-case demographics,
> diagnosis, and treatment response, plus any longitudinal visit / treatment-cycle / adverse-event data.

**Evaluates:** distinguishing the **per-case clinical detail** that exists (demographic + diagnosis via
`caseDetail` / `caseOverview` / `casesByStudyId`) from the **longitudinal clinical-event nodes**
(`visit`, `cycle`, `adverse_event`, `physical_exam`, `vital_signs`, `disease_extent`, prior
therapy/surgery) exposed via the `*NodeData(study_code)` queries — and probing
`clinicalDataNodeCounts` *first* instead of querying empty nodes. Note: `study`/`caseDetail`/
`casesByStudyId`/`*NodeData` take the plain designation **`"UBC01"`**, while the `searchCases`/
`caseOverview` `study` facet takes the display string **`"UBC01 (000004)"`** — the keys are not
interchangeable.

**Trap:** UBC01 is typed `clinical_study_type: "Clinical Trial"`, so an agent expects visits, cycles,
and adverse events. In fact **every longitudinal event node is empty for UBC01** (and for all studies
except COTC007B and PRECINCT01). An empty `*NodeData` / `clinicalDataNodeCounts` return here is
**expected, not a bug** — and `numberOfAliquots` is always 0 (ICDC has no aliquot layer). A skill-less
agent reports the empty nodes as an error or keeps retrying.

**Expected result (verified ground truth):**
- Study metadata: `study(clinical_study_designation: "UBC01")` → name *"Antitumor Activity and
  Molecular Effects of Vemurafenib in Dogs with BRAF-mutant Bladder Cancer,"* `clinical_study_type
  "Clinical Trial"`, `accession_id "000004"`. `humanRelevanceNodeData(["UBC01"])` →
  `relevant_human_cancer ["Bladder Cancer"]`.
- **Per-case detail exists: 38 cases** (`casesByStudyId("UBC01")` / `caseOverview(study: ["UBC01
  (000004)"])`) — 34 Bladder Cancer + 4 Healthy Control. Each `caseDetail` carries breed, sex,
  `patient_age_at_enrollment`, weight, stage, and **`best_response`** — distribution across the 38:
  **Stable Disease 17, Partial Response 12, Not Applicable 4 (the controls), Not Determined 3,
  Progressive Disease 2**. **83 samples, 170 files** (`sampleCountOfStudy` / `fileCountOfStudy`).
- **Longitudinal event nodes are all empty:** `clinicalDataNodeCounts(study_code: "UBC01")` →
  `cycle 0, visit 0, adverse_event 0, physical_exam 0, vital_signs 0, disease_extent 0, prior_therapy
  0, prior_surgery 0` (and follow_up/off_treatment/off_study/agent/lab_exam = 0). The agent should
  report this as "no longitudinal event data was loaded for UBC01," not as a failure. (For contrast,
  the agent may note **COTC007B** is the only study rich in visits/exams/vitals/lesions and
  **PRECINCT01** is the only one with adverse events — both are the skill's own examples.)

**Pass:** returns the per-case demographic/diagnosis/`best_response` detail for UBC01's 38 cases,
**and** correctly reports the longitudinal `*NodeData` nodes as empty/not-loaded for this study
(ideally after a `clinicalDataNodeCounts` probe) — framing the empty event data as expected.
**Fail:** claims UBC01 has visit/cycle/adverse-event rows (fabrication), reports the empty nodes as an
error/bug, retries indefinitely, or returns no per-case detail at all.

**Checks (machine-gradeable):**
- `number: ubc01_cases ≈ 38 (±10%)` and `number: ubc01_files ≈ 170 (±15%)`.
- `substring_any: ["best response", "Partial Response", "Stable Disease"]` — surfaced the real per-case clinical detail.
- `substring: "Vemurafenib"` (or "BRAF") — identified the right study.
- `behavior: probed clinicalDataNodeCounts (or the *NodeData queries) and reported the event nodes as empty/not-loaded`
- `behavior: framed the empty visit/cycle/adverse_event result as expected, not as an error or a retry loop`
- `must_not_contain: ["adverse events recorded for UBC01", "visit records for UBC01", "treatment cycles for UBC01"]` — no fabricated longitudinal rows.

---

## Query 5 — Files → CRDC DRS → manifest, no byte download

**Prompt:**
> List the files for the UBC01 study (or for a bladder-cancer case) and tell me exactly how I'd
> download them.

**Evaluates:** that the agent gets the file records (`filesOfStudy` / `filesOfCase` / a facet cohort's
`fileIds`), resolves the **CRDC DRS id** + access info via `fileDetail`/`fileInfo` (these carry `GUID`
/ `acl` / `file_location`; the raw `file` node does **not**), and routes downloading through DRS or a
**`createManifest`** CSV → Cancer Genomics Cloud. **The ICDC API never streams file bytes.**

**Trap:** claiming a direct HTTP/GraphQL download from ICDC, or asking for `acl`/`GUID` on the raw
`file` node (→ `FieldUndefined`). The API returns *identifiers and an `s3://` location only*; bytes are
fetched out-of-band via the DRS-issued signed URL or staged into CGC.

**Expected result (verified ground truth):**
- `filesOfStudy(study_code: "UBC01")` lists real files (UBC01 has **170**), e.g.
  `UBC01-793-142-Vm30-c.bam` (RNA Sequence File, bam, ≈4.30 GB, uuid
  `c3f523d1-fe5b-5696-974b-c1c4fbd87bd0`) and its `.bai` index (uuid
  `b29e3fb1-8d70-5b63-8dbd-0aabdc2f8831`).
- `fileDetail(file_ids: ["c3f523d1-fe5b-5696-974b-c1c4fbd87bd0"])` →
  `GUID "dg.4DFC/c3f523d1-fe5b-5696-974b-c1c4fbd87bd0"`, `acl "['Open']"`,
  `file_location "s3://nci-cbiit-caninedatacommons-file/Final/UBC01/UBC01-793-142-Vm30-c.bam"`,
  `md5sum "fb8761baa32d00e0acf48f77e3761785"`. (`fileInfo` returns the minimal DRS record: `GUID`,
  `md5`, `size`, `acl`.)
- Download path: the `GUID` is a CRDC DRS object —
  **`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`** — resolve it (e.g. POST to
  `https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/dg.4DFC/<uuid>/access/s3`) for a signed S3 URL,
  or build a manifest: `createManifest(uuid: [...])` returns CSV text whose header includes a
  **`drs_uri`** column (`name,drs_uri,Study Code,Case ID,…` with `dg.4DFC/…` ids) — import it into the
  **Cancer Genomics Cloud (CGC)**. All ICDC files are `acl ['Open']`, so no credential is needed.

**Pass:** lists real files with uuids, produces a DRS id of the form `dg.4DFC/<uuid>` (via
`fileDetail`/`fileInfo`), and explains downloading via CRDC DRS / `createManifest` → CGC — explicitly
noting ICDC itself does not stream bytes.
**Fail:** claims a direct ICDC byte download, requests `GUID`/`acl` on the raw `file` node, invents
uuids, or omits the DRS/manifest hand-off.

**Checks (machine-gradeable):**
- `regex: drs_id matches dg\.4DFC/[0-9a-f-]{36}` — a correctly shaped CRDC DRS id is returned.
- `substring_any: ["UBC01-793-142-Vm30", ".bam", ".bai"]` — names a real UBC01 file.
- `substring_any: ["createManifest", "drs_uri", "Cancer Genomics Cloud", "CGC", "nci-crdc.datacommons.io"]` — names the correct download hand-off.
- `substring_any: ["Open", "acl"]` — recognizes the files are open-access.
- `behavior: resolved the DRS id via fileDetail/fileInfo (not from the raw file node)`
- `must_not_contain: ["download the bytes from the API", "the API returns the file contents", "GraphQL response contains the file data", "streamed the file"]` — no claim of a direct ICDC byte download.

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
