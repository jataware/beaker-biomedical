# Expect

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

# Failure Cases

**Fail:** claims the API serves the participant dataset, fabricates a PBCS dbGaP accession, or presents
the bare `data_file_uuid` as the DRS id.

# Automated Checks

```yaml
checks:
  - substring_all: ["PBCS_Data_Dictionary_PSDC_Core_Variables", "Open Access"]
  - regex: 'drs://nci-crdc\.datacommons\.io/dg\.4DFC/[0-9a-f-]+'
  - substring: "6b9c5c3c-8a04-5700-b9a6-65cca3e6c65b"
  - substring_any: ["not applicable", "no dbgap", "no dbGaP accession"]
  - must_not_contain: ["serves participant-level", "download the participant data from the API", "phs"]
  - behavior: "reported PBCS dbgap_accession_id verbatim (\"Not Applicable\") instead of inventing a phs accession"
```
