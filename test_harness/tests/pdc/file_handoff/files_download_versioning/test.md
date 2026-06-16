---
name: "Files + download + version resolution + runtime robustness"
description: "This tests resolving `pdc_study_id` to the version-specific `study_id` via `studyCatalog`, signed-URL download via `filesPerStudy` with md5 verification, and retrying PDC's transient `null` payloads."
---
List the processed protein-report files for study PDC000127, download one, and verify it's intact.
