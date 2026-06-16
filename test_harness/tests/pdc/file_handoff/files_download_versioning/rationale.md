# Intended Behavior

The agent resolves the version-specific id with `studyCatalog(pdc_study_id: "PDC000127")` → latest `study_id = dbe94609-…` (`is_latest_version = "yes"`), lists real files via `filesPerStudy`, fetches a working pre-signed `signedUrl { url }`, and verifies the downloaded file's md5 against the returned `md5sum` — handling at least one transient null response with a retry.

# Incorrect Behavior

The agent passes `pdc_study_id` where `study_id` is required (or uses a stale version UUID), crashes on a transient `{"data": null}` (HTTP 200, no `errors`) instead of retrying, reuses an expired signed URL, or claims a successful download with no checksum check.
