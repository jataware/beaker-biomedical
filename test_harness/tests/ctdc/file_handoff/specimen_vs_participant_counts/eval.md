# Expect

**Expected result (verified ground truth):**
- `specimenCountBySpecimenType` (per-specimen, sums to **1,140** ≫ 248): **Streck Blood to VARI 344,
  EDTA Blood 341, FFPE Block 140, Formalin Fixed Tissue 65, Bone Marrow Aspirate 56, …** A given type
  like **EDTA Blood = 341 specimens** (drawn from 234 participants) — the 341 is specimens, not
  patients.
- `dataFileCountByDataFileType` (per-file, sums to **2,033**): **Radiology Imaging 1,864 (DICOM),
  Variant Call File 85 (vcf), Variant Report 84 (pdf).**
- A real file row (`fileOverview(data_file_type: ["Variant Call File"], first: 1)`):
  `data_file_name = "MSB-00140-06-somatic-mutations-CTDCv1"`, `data_file_format = "vcf"`,
  `data_file_uuid = "dg.4DFC/CC00EEF6-1730-40B3-9FA6-3D8FCD39EB83"`,
  `drs_uri = "drs://nci-crdc.datacommons.io/dg.4DFC/CC00EEF6-1730-40B3-9FA6-3D8FCD39EB83"`.
  **Download = resolve that DRS id** (e.g.
  `POST https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/<dg.4DFC/...>/access/s3` → signed URL) or
  load the uuid set into a Cancer Genomics Cloud manifest. The CTDC GraphQL API itself returns no bytes.
**Pass:** states the specimen-type count as **specimens** (e.g. ~341 EDTA Blood / ~1,140 total
specimens), explicitly distinct from the 248 participants; produces a real `dg.4DFC/<uuid>` DRS id; and
explains download is via DRS resolution / CGC, not a direct API call.

# Failure Cases

**Fail:** reports a specimen-type or file count as a number of patients; claims the API/GraphQL endpoint
directly downloads the files; or invents a `signedUrl`/download URL field on the file record.

# Automated Checks

```yaml
checks:
  - number:
      name: "total_specimens"
      target: 1140
      tolerance_percent: 5
  - number:
      name: "edta_blood_specimens"
      target: 341
      tolerance_percent: 10
  - number:
      name: "vcf_files"
      target: 85
      tolerance_percent: 15
  - regex:
      name: "returned DRS id"
      pattern: '(?i)dg\.4DFC/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
  - substring_any: ["drs://nci-crdc.datacommons.io", "ga4gh/drs", "cancer genomics cloud", "CGC"]
  - behavior: "described specimen/file counts as per-specimen/per-file, distinct from the 248 participants"
  - must_not_contain: ["341 participants", "341 patients", "1140 participants", "1140 patients"]
  - must_not_contain: ["downloaded the file via the api", "graphql endpoint returns the file bytes", "signedUrl"]
```
