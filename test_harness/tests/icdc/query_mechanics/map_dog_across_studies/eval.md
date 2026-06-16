# Expect

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

# Failure Cases

**Trap:** treating each `case_id` as a distinct animal (so the dog's data looks like two unrelated
patients), or never resolving the shared `canine_individual_id`. A skill-less agent also tends to grab
the worked-example dog; a generalizing agent finds a fresh one.
**Fail:** treats the two case_ids as separate dogs, fails to find the shared individual, or reuses the
example dog "0009" without finding a fresh one.

# Automated Checks

```yaml
checks:
  - count_at_least:
      name: "studies_for_dog"
      min: 2
  - count_at_least:
      name: "case_ids_for_dog"
      min: 2
  - regex:
      name: "individual_id"
      pattern: '\b0\d{3}\b'
  - substring_any: ["UBC01", "UBC02"]
  - behavior: "resolved a shared canine_individual via multiStudyCases or the canine_individual node"
  - must_not_contain: ["0009"]
```
