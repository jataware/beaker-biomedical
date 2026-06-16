# Expect

**Traps:**
1. Passing `pdc_study_id` where `study_id` is required, or using a stale/non-latest version UUID.
2. Treating a transient `{"data": null}` (HTTP 200, no `errors`) — or a populated result with a nested
   `pagination: null` — as a hard failure.
3. Caching/reusing an expired signed URL.
**Expected result (verified ground truth):**
- `studyCatalog(pdc_study_id: "PDC000127")` → latest version `study_id =
  dbe94609-1fb3-11e9-b7f8-0a80fada099c` (study_version 1, `is_latest_version = "yes"`).
- `filesPerStudy(study_id: …)` returns real files with a working `signedUrl { url }` (a pre-signed
  S3 link, no auth headers needed). `filesCountPerStudy` shows ~9 `file_type` × `data_category`
  combinations (e.g. *Peptide Spectral Matches / Open Standard* = 575 files).
- Downloaded file's computed md5 matches the returned `md5sum`.
**Pass:** resolves the latest `study_id`, lists real files, fetches a signed URL, and verifies the
checksum — handling at least one null/retry gracefully.

# Failure Cases

**Fail:** ID-type error, crash on a null response, or claims a successful download with no checksum check.

# Automated Checks

```yaml
checks:
  - substring: "dbe94609-1fb3-11e9-b7f8-0a80fada099c"
  - behavior: "resolved pdc_study_id → version-specific study_id via studyCatalog (is_latest_version=\"yes\"); did NOT pass pdc_study_id where study_id is required, nor a stale version UUID"
  - substring_any: ["signedUrl", "signed URL", "presigned", "s3"]
  - behavior: "computed the downloaded file's md5 and compared it to the returned md5sum"
  - behavior: "handled at least one transient null payload (HTTP 200 {\"data\": null} or nested pagination:null) by retrying, did not crash"
  - number:
      name: "peptide_spectral_matches_open_standard_files"
      target: 575
      tolerance_percent: 15
  - must_not_contain: ["7-day URL has not expired", "reused the cached signed URL"]
```
