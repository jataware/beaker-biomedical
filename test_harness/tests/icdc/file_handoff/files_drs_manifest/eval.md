# Expect

**`createManifest`** CSV → Cancer Genomics Cloud. **The ICDC API never streams file bytes.**
**Expected result (verified ground truth):**
- `filesOfStudy(study_code: "UBC01")` lists real files (UBC01 has **170**), e.g.
  `UBC01-793-142-Vm30-c.bam` (RNA Sequence File, bam, ≈4.30 GB, uuid
  `c3f523d1-fe5b-5696-974b-c1c4fbd87bd0`) and its `.bai` index (uuid
  `b29e3fb1-8d70-5b63-8dbd-0aabdc2f8831`).
- `fileDetail(file_ids: ["c3f523d1-fe5b-5696-974b-c1c4fbd87bd0"])` →
  `GUID "dg.4DFC/c3f523d1-fe5b-5696-974b-c1c4fbd87bd0"`, `acl "['Open']"`,
  `file_location "s3://nci-cbiit-caninedatacommons-file/Final/UBC01/UBC01-793-142-Vm30-c.bam"`,
  `md5sum "fb8761baa32d00e0acf48f77e3761785"`. (`fileInfo` returns the minimal DRS record: `GUID`,
  `md5`, `size`, `acl`.)
- Download path: the `GUID` is a CRDC DRS object —
  **`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`** — resolve it (e.g. POST to
  `https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/dg.4DFC/<uuid>/access/s3`) for a signed S3 URL,
  or build a manifest: `createManifest(uuid: [...])` returns CSV text whose header includes a
  **`drs_uri`** column (`name,drs_uri,Study Code,Case ID,…` with `dg.4DFC/…` ids) — import it into the
  **Cancer Genomics Cloud (CGC)**. All ICDC files are `acl ['Open']`, so no credential is needed.
**Pass:** lists real files with uuids, produces a DRS id of the form `dg.4DFC/<uuid>` (via
`fileDetail`/`fileInfo`), and explains downloading via CRDC DRS / `createManifest` → CGC — explicitly
noting ICDC itself does not stream bytes.

# Failure Cases

**Trap:** claiming a direct HTTP/GraphQL download from ICDC, or asking for `acl`/`GUID` on the raw
`file` node (→ `FieldUndefined`). The API returns *identifiers and an `s3://` location only*; bytes are
fetched out-of-band via the DRS-issued signed URL or staged into CGC.
**Fail:** claims a direct ICDC byte download, requests `GUID`/`acl` on the raw `file` node, invents
uuids, or omits the DRS/manifest hand-off.

# Automated Checks

```yaml
checks:
  - regex:
      name: "drs_id"
      pattern: 'dg\.4DFC/[0-9a-f-]{36}'
  - substring_any: ["UBC01-793-142-Vm30", ".bam", ".bai"]
  - substring_any: ["createManifest", "drs_uri", "Cancer Genomics Cloud", "CGC", "nci-crdc.datacommons.io"]
  - substring_any: ["Open", "acl"]
  - behavior: "resolved the DRS id via fileDetail/fileInfo (not from the raw file node)"
  - must_not_contain: ["download the bytes from the API", "the API returns the file contents", "GraphQL response contains the file data", "streamed the file"]
```
