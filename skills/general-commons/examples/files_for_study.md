# List a study's files (and why there's no direct download)

`files(phs_accession: …)` returns per-file metadata. **This API does not download data** — `file_id` is
a CRDC DRS identifier and data access happens on the Cancer Genomics Cloud (CGC) by Velsera via a
manifest. See [../references/FILES.md](../references/FILES.md).

## Example

```python
import requests, json
URL = "https://general.datacommons.cancer.gov/v1/graphql/"
def gc(q, tries=3):
    for _ in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=120).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        if b.get("data") is not None: return b["data"]
    raise RuntimeError("GC returned null data")

PHS = "phs001287"

# 1. How many files, and is the study open or controlled?
print(gc('{ filesCount(phs_accession:"%s") '
         'studies(phs_accessions:["%s"]) { study_access acl file_types_and_format } }' % (PHS, PHS)))

# 2. List files. file_types is a filter (list of strings). Page with first/offset (default is 10!).
files = gc('{ files(phs_accession:"%s" first:100 offset:0) '
           '{ file_id file_name file_type file_size md5sum file_url_in_cds is_supplementary_file release_datetime } }'
           % PHS)["files"]
print(len(files), "files (first page)")
for f in files[:3]:
    print(f'{f["file_type"]:18} {int(f["file_size"]):>12} bytes  {f["file_id"]}  {f["file_name"]}')
# GCT/Res Format    25920500 bytes  dg.4DFC/0359521d-...  pdac-25-JHU-TMT11-126C-...gct
#   ^ file_id is a GA4GH DRS id (dg.4DFC/<uuid>), NOT a URL. file_url_in_cds is usually "".

# 3. Drop supplementary docs for an analysis set; sum sizes (file_size is a STRING).
primary = [f for f in files if f["is_supplementary_file"] not in ("true", "True", "Yes")]
total_gb = sum(int(f["file_size"]) for f in primary if f["file_size"]) / 1e9
print(f"{len(primary)} primary files, {total_gb:.1f} GB")

# 4. Filter by type / release window.
bams = gc('{ files(phs_accession:"%s" file_types:["bam"] released_range_start:"2024-01-01" first:50) '
          '{ file_id file_name file_size } }' % PHS)["files"]
```

## There is no `download()` — point users at CGC

```python
# DON'T: there is no signed URL or HTTP link to GET. file_url_in_cds is typically empty, and file_id is
# a DRS id. To actually get bytes:
#   1. Assemble the file set here (the file_id + metadata rows = your manifest).
#   2. For controlled-access studies (study_access == "Controlled"), the user needs dbGaP authorization
#      for the study's acl (e.g. ['phs001287']).
#   3. Load the manifest into a Cancer Genomics Cloud (CGC by Velsera) workspace and analyze in-cloud.
print("Access GC files via a CGC manifest workflow, not a direct download. See references/FILES.md")
```

## Notes

- **`file_id` is a DRS id**, not an HTTP URL; `file_url_in_cds` is frequently `""`. The API is
  metadata-only.
- **`first` defaults to 10** — set it / loop ([paginate.md](paginate.md)). `filesCount` gives the total.
- **`file_size` is a String of bytes** — cast before arithmetic.
- **Open vs controlled** lives on the Study (`study_access`, `acl`, `data_access_level`); searching
  metadata never needs auth, but downloading controlled data needs dbGaP authorization.
- To learn a file's modality, join its `file_id` to `genomic_info` / `proteomics` / `images` /
  `multiplex_microscopies` / `non_dicom*` ([../references/DATA-TYPES.md](../references/DATA-TYPES.md)).
</content>
