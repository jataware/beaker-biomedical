# Downloading files from GDC

## `/data` endpoint

### Single file (GET)

```bash
curl --remote-name --remote-header-name 'https://api.gdc.cancer.gov/data/<uuid>'
```

The response body **is** the file. `--remote-header-name` makes curl honor the
`Content-Disposition: filename=...` header.

In Python:

```python
import re, requests
r = requests.get(f"https://api.gdc.cancer.gov/data/{file_id}")
r.raise_for_status()
name = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
open(name, "wb").write(r.content)
```

### Multiple files (GET, small batches)

```bash
curl -OJ 'https://api.gdc.cancer.gov/data/uuid1,uuid2,uuid3'
```

Returns a `.tar.gz` archive. Use POST for more than a handful of UUIDs.

### Multiple files (POST, recommended for batches)

```bash
curl -OJ --request POST --header 'Content-Type: application/json' \
  --data '{"ids":["uuid1","uuid2","uuid3"]}' \
  'https://api.gdc.cancer.gov/data'
```

Form-encoded alternative:

```bash
curl -OJ --request POST \
  --data 'ids=uuid1&ids=uuid2&ids=uuid3' \
  'https://api.gdc.cancer.gov/data'
```

### Related files

Append `?related_files=true` to bundle the index files alongside the primary file. Currently includes:

- BAM index files (`.bai`)
- VCF index files (`.tbi`)

```bash
curl -OJ 'https://api.gdc.cancer.gov/data/<bam-uuid>?related_files=true'
```

### Uncompressed tar

Append `?tarfile` to get a single `.tar` instead of `.tar.gz`.

### Controlled-access files

Add `X-Auth-Token`. File must have `access=controlled`, and the user must be authorized for its
`acl` (dbGaP accession).

```bash
token=$(cat gdc-token-text-file.txt)
curl -OJ -H "X-Auth-Token: $token" 'https://api.gdc.cancer.gov/data/<uuid>'
```

## `/manifest` endpoint (for the GDC Data Transfer Tool)

For large transfers — hundreds of GB+ — the Data Transfer Tool (`gdc-client`) is the right tool. It
needs a *manifest* TSV listing UUIDs and metadata.

### Build a manifest from a UUID list

```bash
curl -OJ 'https://api.gdc.cancer.gov/manifest/uuid1,uuid2,uuid3'
```

POST works too — same body shape as `/data`.

### Build a manifest from a search query

Append `&return_type=manifest` to any `/files` query:

```bash
curl -OJ 'https://api.gdc.cancer.gov/files?filters=...&return_type=manifest'
```

> ⚠ **`return_type=manifest` ignores `size`** — it always returns every matching record. Cap the filter
> upstream instead.

### Using the manifest with gdc-client

```bash
gdc-client download -m manifest.txt           # open access
gdc-client download -m manifest.txt -t TOKEN  # controlled access
```

## BAM slicing

Endpoint: `/slicing/view/{file_id}`. Works on harmonized BAMs in the Portal only.

### Region (GET)

```bash
curl -H "X-Auth-Token: $token" \
  'https://api.gdc.cancer.gov/slicing/view/<bam-uuid>?region=chr1&region=chr2:10000&region=chr3:10000-20000' \
  --output slice.bam
```

### Region (POST JSON)

```bash
curl -H "X-Auth-Token: $token" --request POST \
  --header "Content-Type: application/json" \
  --data '{"regions":["chr1","chr2:10000","chr3:10000-20000"]}' \
  'https://api.gdc.cancer.gov/slicing/view/<bam-uuid>' \
  --output slice.bam
```

### Gene (HGNC / GENCODE v36)

```bash
curl -H "X-Auth-Token: $token" --request POST \
  --header "Content-Type: application/json" \
  --data '{"gencode":["BRCA1","BRCA2"]}' \
  'https://api.gdc.cancer.gov/slicing/view/<bam-uuid>' \
  --output brca12.bam
```

### Unmapped reads

```json
{"regions":["unmapped"]}
```

### Notes & gotchas

- The sliced BAM contains all reads overlapping (entirely or partially) the requested region.
  Open-ended regions like `chr2:10000` extend to the chromosome end.
- A region with no reads is **not** an error — you'll get a valid BAM containing just the header.
- Empty query (no `region`/`gencode`) returns the BAM header only — useful for inspecting references.
- **The slice has no BAI.** Generate one with `samtools index slice.bam`.
- Most slice files are < 2 GB; large slices over flaky links can be truncated. If `samtools view`
  reports `EOF marker is absent`, re-run the request.
- HTTP error codes: 400 (malformed region), 403 (unauthorized / no token), 404 (no BAM), 504 (BAI not
  found on source BAM).

## End-to-end pattern: search → download

```python
import json, re, requests

# 1. Find UUIDs matching a filter
files_endpt = "https://api.gdc.cancer.gov/files"
filters = {"op":"and","content":[
    {"op":"in","content":{"field":"cases.project.project_id","value":["TCGA-KIRC"]}},
    {"op":"=","content":{"field":"experimental_strategy","value":"RNA-Seq"}},
    {"op":"=","content":{"field":"cases.samples.sample_type","value":"Solid Tissue Normal"}},
    {"op":"=","content":{"field":"access","value":"open"}},
]}
r = requests.post(files_endpt,
                  json={"filters": filters, "fields": "file_id", "size": "200"},
                  headers={"Content-Type": "application/json"})
ids = [hit["file_id"] for hit in r.json()["data"]["hits"]]

# 2. Download
data_endpt = "https://api.gdc.cancer.gov/data"
r = requests.post(data_endpt, json={"ids": ids},
                  headers={"Content-Type": "application/json"})
name = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
open(name, "wb").write(r.content)
```
