# Expect

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

# Failure Cases

**Trap:** UBC01 is typed `clinical_study_type: "Clinical Trial"`, so an agent expects visits, cycles,
and adverse events. In fact **every longitudinal event node is empty for UBC01** (and for all studies
except COTC007B and PRECINCT01). An empty `*NodeData` / `clinicalDataNodeCounts` return here is
**Fail:** claims UBC01 has visit/cycle/adverse-event rows (fabrication), reports the empty nodes as an
error/bug, retries indefinitely, or returns no per-case detail at all.

# Automated Checks

```yaml
checks:
  - number:
      name: "ubc01_cases"
      target: 38
      tolerance_percent: 10
  - number:
      name: "ubc01_files"
      target: 170
      tolerance_percent: 15
  - substring_any: ["best response", "Partial Response", "Stable Disease"]
  - substring: "Vemurafenib"
  - behavior: "probed clinicalDataNodeCounts (or the *NodeData queries) and reported the event nodes as empty/not-loaded"
  - behavior: "framed the empty visit/cycle/adverse_event result as expected, not as an error or a retry loop"
  - must_not_contain: ["adverse events recorded for UBC01", "visit records for UBC01", "treatment cycles for UBC01"]
```
