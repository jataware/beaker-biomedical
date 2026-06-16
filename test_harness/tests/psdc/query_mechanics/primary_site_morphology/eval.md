# Expect

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

# Failure Cases

**Fail:** reports a `FieldUndefined` error as the answer, fabricates site/morphology names, or returns
NLST's data.

# Automated Checks

```yaml
checks:
  - set_contains:
      name: "PLCO_primary_sites"
      members: ["prostate gland", "breast", "lung", "colorectum"]
  - number:
      name: "PLCO_prostate_site"
      target: 11129
      tolerance_percent: 10
  - substring_any: ["adenocarcinoma", "8140/3"]
  - count_at_least:
      name: "PLCO_primary_sites"
      min: 8
  - must_not_contain: ["primary_site", "FieldUndefined"]
  - behavior: "selected { group subjects } (and group_code for morphology) on primarySiteMorphology — not primary_site/count"
```
