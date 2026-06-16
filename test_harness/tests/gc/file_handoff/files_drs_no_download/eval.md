# Expect

**Expected result (verified ground truth):**
- `studies(phs_accessions:["phs001714"])` → KF-OS, *"Gabriella Miller Kids First Pediatric Research
  Program: An Integrated Clinical and Genomic Analysis of Treatment Failure in Pediatric Osteosarcoma"*,
  **`study_access = "Controlled"`**, **`acl = ['phs001714.c1']`**, `authz = ['/programs/phs001714.c1']`.
- `filesCount(phs_accession:"phs001714")` → **12,727** files.
- `files(...)` returns `file_id` like **`dg.4DFC/00006dc0-49b8-4c63-a0ae-3bc6886e5008`** — a GA4GH DRS
  id, not a URL. `filesInList(phs_accession:["phs001714"])` gives the manifest fields:
  `drs_uri = drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>` (e.g.
  `drs://nci-crdc.datacommons.io/dg.4DFC/a230d9b3-ac62-474b-874f-57711c17085d`) and
  **`accesses = ["Controlled"]`**.
- Correct download answer: this API does **not** download bytes. Build a manifest from
  `file_id`/`drs_uri`, obtain **dbGaP authorization** for `phs001714.c1` (controlled), then load the
  manifest into a **CGC (Velsera)** workspace to access/analyze the files in-cloud.
**Pass:** lists files showing the DRS `file_id`/`drs_uri` (`dg.4DFC/…`); states the study is Controlled
and needs **dbGaP** authorization; routes the actual access through a **CGC manifest** workflow.

# Failure Cases

**Trap(s):**
1. Promising a direct download / a signed HTTP URL. There is **no `signedUrl`/`url` field** on `File`
   (`{ files{ signedUrl } }` → `FieldUndefined`), unlike PDC. `file_url_in_cds` here is a **controlled
   `s3://kf-study-...` path**, not a public HTTP link — accessing it still needs authorization.
2. Ignoring that the study is **Controlled** (skipping the dbGaP authorization step).
3. Treating the DRS `file_id` as an HTTP URL to GET.
**Fail:** promises a direct download or a signed URL; treats `file_id`/`drs_uri` as an HTTP link;
omits the controlled-access/dbGaP step.

# Automated Checks

```yaml
checks:
  - regex: 'dg\.4DFC/[0-9a-f-]+'
  - substring_any: ["drs://nci-crdc.datacommons.io", "drs_uri"]
  - substring_all: ["Controlled", "dbGaP"]
  - substring_any: ["Cancer Genomics Cloud", "CGC", "Velsera"]
  - substring: "[\"phs001714\"]"
  - must_not_contain: ["signed url", "signedUrl", "direct download", "download link"]
  - behavior: "described the file_id/drs_uri as a DRS identifier resolved via a CGC manifest, not as an HTTP URL to GET"
```
