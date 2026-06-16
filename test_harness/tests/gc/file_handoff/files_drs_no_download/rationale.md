# Intended Behavior

The agent resolves the study (`studies(phs_accessions:["phs001714"])` → KF-OS, `study_access "Controlled"`, `acl ['phs001714.c1']`), counts ~12,727 files, and lists files whose `file_id`/`drs_uri` are GA4GH DRS ids (`dg.4DFC/<uuid>`), not URLs. It states the study is Controlled and needs dbGaP authorization, and that bytes are accessed by building a manifest and loading it into a Cancer Genomics Cloud (Velsera) workspace — this API does not download bytes.

# Incorrect Behavior

The agent promises a direct download or signed HTTP URL (there is no `signedUrl`/`url` field on `File`; `file_url_in_cds` is a controlled `s3://` path, not a public link), treats the DRS `file_id`/`drs_uri` as an HTTP link to GET, or skips the controlled-access/dbGaP step.
