# Files, DRS ids & download manifests

ICDC returns file *metadata* and *identifiers*; bytes are fetched out-of-band. Uses the `icdc()` helper
from [quickstart.md](quickstart.md). Background: [../references/FILES.md](../references/FILES.md).

## Get a cohort's / case's / study's files

```python
# files of a case
icdc('{ filesOfCase(case_id: "NCATS-COP01-CCB010015") '
     '{ file_name file_type file_format file_size uuid parent } }')["filesOfCase"]

# files of a study (study_code accepts the designation OR the accession_id)
icdc('{ filesOfStudy(study_code: "OSA01", first: 5) '
     '{ file_name file_type file_format file_size uuid } }')["filesOfStudy"]

# files of a facet cohort: searchCases gives the fileIds (see faceted_search.md)
file_ids = icdc('{ searchCases(diagnosis:["Osteosarcoma"], file_format:["bam"]) { fileIds } }'
                )["searchCases"]["fileIds"]
```

## Get the DRS id and access info

The DRS `GUID` and `acl` live on `fileDetail` / `fileInfo`, **not** the raw `file` node.

```python
icdc('''
{ fileDetail(file_ids: ["bf7ae08f-0afe-5aa5-969a-de9a17ac0f2f"]) {
    file_name file_format file_size md5sum uuid
    GUID            # CRDC DRS id
    acl
    file_location } }
''')["fileDetail"][0]
# {'file_name': '010015_0103_sorted.bam', 'file_format': 'bam', 'file_size': 17545870661.0,
#  'uuid': 'bf7ae08f-0afe-5aa5-969a-de9a17ac0f2f',
#  'GUID': 'dg.4DFC/bf7ae08f-0afe-5aa5-969a-de9a17ac0f2f',
#  'acl': "['Open']",
#  'file_location': 's3://nci-cbiit-caninedatacommons-file/Final/NCATS/NCATS01/Bam-files/010015_0103_sorted.bam'}
```

The `GUID` `dg.4DFC/<uuid>` is a CRDC DRS object: `drs://nci-crdc.datacommons.io/dg.4DFC/<uuid>`. All
current ICDC files are `acl ['Open']` — no dbGaP/controlled tier — so no credential is needed.

## Resolve the DRS id to a signed download URL

```python
import requests
guid = "dg.4DFC/bf7ae08f-0afe-5aa5-969a-de9a17ac0f2f"
r = requests.post(f"https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/{guid}/access/s3")
# -> {"url": "https://<signed-s3-url>"}  ; then GET that url to download the bytes
```

(`fileInfo(file_ids:[...])` is the minimal DRS record: `GUID`, `md5`, `size`, `acl`, `url`.)

## Build a manifest for the Cancer Genomics Cloud

`createManifest` returns the **manifest CSV content directly** (header + one row per file, with DRS
uri and joined clinical columns). Save it and import into a CGC project for analysis.

```python
csv_text = icdc('{ createManifest(uuid: %s) }'
                % str(file_ids).replace("'", '"'))["createManifest"]
open("cohort_manifest.csv", "w").write(csv_text)
# header: name,drs_uri,Study Code,Case ID,File Type,File Format,File Size,md5sum,File UUID,File Location, ...
```

> The website's "download manifest" button instead calls a *separate* interoperation microservice
> (`storeManifest`, `POST /api/interoperation/graphql`), which uploads the CSV and returns a
> time-limited signed CloudFront URL. You usually don't need it — `createManifest` already hands you
> the CSV. Spec: [../assets/interoperation-openapi.yaml](../assets/interoperation-openapi.yaml).

## The analysis story

ICDC pairs with the **Cancer Genomics Cloud (CGC) by Velsera** — build a cohort here, export the
manifest, and run tools (RNA-Seq, variant calling, …) on CGC against the staged files. The API itself
never streams bytes.
