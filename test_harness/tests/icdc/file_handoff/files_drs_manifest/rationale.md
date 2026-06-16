# Intended Behavior

The agent lists real file records (e.g. `filesOfStudy(study_code: "UBC01")`, 170 files), resolves the CRDC DRS id and access info via `fileDetail`/`fileInfo` (which carry the `GUID dg.4DFC/<uuid>`, `acl`, `file_location`, and `md5sum`), and explains downloading via CRDC DRS resolution or a `createManifest` CSV imported into the Cancer Genomics Cloud. All ICDC files are `acl ['Open']`, and the ICDC API itself never streams bytes.

# Incorrect Behavior

The agent claims a direct HTTP/GraphQL download from ICDC, asks for `acl`/`GUID` on the raw `file` node (which returns `FieldUndefined`), invents uuids, or omits the DRS/manifest hand-off.
