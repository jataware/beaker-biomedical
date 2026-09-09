# Files & data access

The CTDC API returns file **metadata and identifiers, not file bytes.** Every download happens
out-of-band via a CRDC DRS id or the Cancer Genomics Cloud.

## Where file records come from

- **Faceted layer:** `fileOverview(...facets)` → `[FileOverview]` is the main file query (browse files
  by participant/diagnosis/specimen/file-type facets). `filesInList(data_file_uuid: [..])` returns rows
  for an explicit uuid list (a manifest). `biospecimen_data_files` / `participant_data_files` join files
  at the specimen / participant level. See [SEARCH.md](SEARCH.md).
- **Per study:** `StudyDataFileByStudyShortName(study_short_name)` → study-level + participant data files.

## A file record

`FileOverview` fields: `data_file_name`, `data_file_type` (e.g. `Radiology Imaging`), `data_file_format`
(`DICOM`, …), `data_file_size` (Float, bytes), `data_file_checksum_value` (+ `_type`),
`data_file_compression_status`, `data_file_uuid`, **`drs_uri`**, `data_file_location`, `association`
(e.g. `["participant"]`), plus the joined clinical context (`participant_id`, `specimen_id`,
`ctep_disease_term`, `study_short_name`, …).

```graphql
{ fileOverview(first: 1) {
    data_file_name data_file_format data_file_type data_file_size
    data_file_uuid drs_uri data_file_location data_file_checksum_value participant_id association } }
# data_file_uuid "dg.4DFC/e2cf5d14-…", drs_uri "drs://nci-crdc.datacommons.io/dg.4DFC/e2cf5d14-…",
# data_file_location null, association ["participant"], format DICOM
```

## The DRS id is the download handle, not a URL

`data_file_uuid` **is** the CRDC DRS id (`dg.4DFC/<uuid>`), and `drs_uri` is its full form
(`drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`). `data_file_location` is **often `null`** — do not
rely on it. To get bytes:

1. **CRDC DRS** — resolve the id, e.g.
   `POST https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/dg.4DFC/<uuid>/access/s3` → a signed URL.
2. **Cancer Genomics Cloud (CGC)** — assemble the `data_file_uuid`/`drs_uri` set into a manifest and
   load it into a CGC project for in-cloud analysis. `getInteropData` exposes CTDC's cross-CRDC
   interoperation links (e.g. imaging files that live in IDC/TCIA).

## Access

CTDC metadata and search are **open-access** (no credential). Studies carry `consent_groups`; where
data is access-controlled, retrieval is governed through CRDC/dbGaP at the DRS layer, not by a token
passed to this API. (`FileOverview` has **no `accesses` field** — unlike some sibling commons.)

## Building a manifest for a cohort

```graphql
# uuids for a facet cohort, then their file rows
{ fileOverview(ctep_disease_term: ["Melanoma"], data_file_format: ["DICOM"], first: 1000)
  { data_file_uuid drs_uri data_file_name data_file_size } }
```

Or resolve a mix of ids to file uuids with
`fileIDsFromList(participant_id: [..], specimen_id: [..], data_file_name: [..])`, then feed them to
`filesInList(data_file_uuid: [..])`. See [../examples/files_and_download.md](../examples/files_and_download.md).

## Tips

- `data_file_size` is a Float of bytes; some images are `DICOM` zips.
- Verify integrity with `data_file_checksum_value` (+ `data_file_checksum_type`) after retrieval.
- `association` tells you whether a file is attached at participant or specimen level.
