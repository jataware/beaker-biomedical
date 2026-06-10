# Files, DRS identifiers & downloading

The ICDC API serves **file metadata, not file bytes.** Every download happens out-of-band: resolve a
CRDC DRS id, or stage a manifest into the Cancer Genomics Cloud.

## What a file record carries

The raw `file` node: `file_name`, `file_type` (e.g. `RNA Sequence File`, `Index File`, `Sequence
Data File`), `file_format` (`bam`, `bai`, `vcf`, `fastq`, `maf`, …), `file_size` (bytes, Float),
`md5sum`, `file_status`, `uuid`, `file_location` (`s3://nci-cbiit-caninedatacommons-file/...`).

The DRS id and access control live on the **`fileDetail`** / **`fileInfo`** convenience queries, not
the bare node:

```graphql
{ fileDetail(file_ids: ["bf7ae08f-0afe-5aa5-969a-de9a17ac0f2f"]) {
    file_name file_format file_size md5sum uuid
    GUID            # "dg.4DFC/bf7ae08f-..."  → the CRDC DRS id
    acl             # "['Open']"  — all current ICDC files are Open-access
    file_location   # "s3://nci-cbiit-caninedatacommons-file/Final/NCATS/.../010015_0103_sorted.bam"
  } }
```

`fileInfo(file_ids:[...])` returns just the DRS essentials: `GUID`, `md5`, `size`, `acl`, `url`.

## Access: all Open today

Every ICDC file is `acl ['Open']` and every study is `study_disposition: "Unrestricted"`. There is
**no controlled-access / dbGaP tier in ICDC** (a difference from some sibling CRDC commons). No
credential is needed to resolve or download.

## Downloading — three paths

1. **CRDC DRS.** The `GUID` `dg.4DFC/<uuid>` is a DRS object id under the CRDC server
   `nci-crdc.datacommons.io`, i.e. `drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`. Resolve it with any
   DRS client (e.g. POST to `https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/dg.4DFC/<uuid>/access/s3`)
   to get a signed URL. The portal's manifest column `drs_uri` is this same id.
2. **Direct `s3://` location.** `file_location` is the bucket path; for Open files the bytes are
   reachable via the DRS-issued signed URL.
3. **Cancer Genomics Cloud (CGC) by Velsera** — the intended analysis path. Build a manifest of the
   files you want and load it into a CGC project; ICDC's bioinformatics tutorials (e.g. RNA-Seq) run on
   CGC. See <https://www.cancergenomicscloud.org/>.

## Building a manifest

- **`createManifest(uuid: [String], order_by, sort_direction, first, offset)` → `String`** returns the
  **manifest CSV content directly** (a header row: `name, drs_uri, Study Code, Case ID, File Type,
  File Format, File Size, md5sum, File UUID, File Location, …` plus the joined clinical columns, then a
  row per file). Write it to a `.csv` and import into CGC.
- The separate **interoperation microservice** (`storeManifest`, a *different* endpoint —
  `POST /api/interoperation/graphql`, spec in
  [../assets/interoperation-openapi.yaml](../assets/interoperation-openapi.yaml)) takes a manifest CSV,
  uploads it to S3, and returns a **time-limited signed CloudFront URL** for the CGC hand-off. It is
  what the website's "download manifest" button calls; you usually don't need it — `createManifest`
  already gives you the CSV. No end-user credential is required for either.

## Getting the file set for a cohort

- A case's files: `filesOfCase(case_id)` (or `filesOfCases(case_ids)`); a study's files:
  `filesOfStudy(study_code)` and study-level `studyFiles(study_codes)`; a sample's: `filesBySampleId`.
- A facet cohort's files: `searchCases(...) { fileIds }`, then `createManifest(uuid: fileIds)` or
  `fileOverview(file_uuids: fileIds)`. See [../examples/files_and_download.md](../examples/files_and_download.md).
- Resolve uuids from names with `fileIdsFromFileName(file_name: ["x.bam"])`.

Note: `numberOfStudyFiles` (currently 30) are files attached at the study level (protocols, summary
matrices); the rest are case/sample-level. `numberOfAliquots` is 0 — ICDC has no aliquot layer.
