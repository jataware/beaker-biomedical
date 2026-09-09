# Files, DRS ids & download

CTDC returns file *metadata* and *identifiers*; bytes are fetched out-of-band via a CRDC DRS id or the
Cancer Genomics Cloud. Uses the `ctdc()` helper from [quickstart.md](quickstart.md). Background:
[../references/FILES.md](../references/FILES.md).

## Get a cohort's / study's files

```python
# files for a facet cohort (across the repository)
files = ctdc('{ fileOverview(ctep_disease_term: ["Melanoma"], first: 1000) '
             '{ data_file_name data_file_format data_file_type data_file_size '
             'data_file_uuid drs_uri participant_id association } }')["fileOverview"]

# files of a specific specimen / participant
ctdc('{ biospecimen_data_files(specimen_id: ["..."]) { data_file_name data_file_uuid drs_uri } }')
ctdc('{ participant_data_files(participant_id: ["MSB-00205"]) { data_file_name data_file_uuid drs_uri } }')

# a study's data files
ctdc('{ StudyDataFileByStudyShortName(study_short_name: "CMB") { list_type } }')
```

## The DRS id is the download handle

A `fileOverview` row:

```python
ctdc('{ fileOverview(first: 1) { data_file_name data_file_format data_file_type data_file_size '
     'data_file_uuid drs_uri data_file_location data_file_checksum_value participant_id association } }'
     )["fileOverview"][0]
# {'data_file_name': '1.3.6.1.4.1.....zip', 'data_file_format': 'DICOM',
#  'data_file_type': 'Radiology Imaging', 'data_file_size': 6386302.0,
#  'data_file_uuid': 'dg.4DFC/e2cf5d14-4686-56c9-96b6-5c6d449a3782',
#  'drs_uri': 'drs://nci-crdc.datacommons.io/dg.4DFC/e2cf5d14-4686-56c9-96b6-5c6d449a3782',
#  'data_file_location': None, 'association': ['participant']}
```

`data_file_uuid` **is** the CRDC DRS id (`dg.4DFC/<uuid>`); `drs_uri` is its full form.
`data_file_location` is **often `None`** — don't depend on it.

## Resolve the DRS id to bytes

```python
import requests
guid = "dg.4DFC/e2cf5d14-4686-56c9-96b6-5c6d449a3782"
r = requests.post(f"https://nci-crdc.datacommons.io/ga4gh/drs/v1/objects/{guid}/access/s3")
# -> {"url": "https://<signed-url>"}  ; then GET that url to download
```

Or assemble the `data_file_uuid` / `drs_uri` set into a manifest and load it into a **Cancer Genomics
Cloud (CGC)** project for in-cloud analysis. `getInteropData` exposes CTDC's cross-CRDC links — many
CTDC imaging files (`data_file_type: "Radiology Imaging"`, DICOM) live in the imaging commons / TCIA.

## Resolve a mix of ids → file uuids

```python
uuids = ctdc('{ fileIDsFromList(participant_id: ["MSB-00205"]) }')["fileIDsFromList"]
rows  = ctdc('{ filesInList(data_file_uuid: %s, first: 1000) { data_file_name drs_uri } }'
             % str(uuids).replace("'", '"'))["filesInList"]
```

## Notes

- `data_file_size` is a Float of bytes; verify integrity with `data_file_checksum_value`
  (+ `data_file_checksum_type`) after retrieval.
- CTDC metadata/search is open; access-controlled *bytes* (where present) are governed at the CRDC DRS
  layer — the API never streams files and `FileOverview` has no `accesses` field.
