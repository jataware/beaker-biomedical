# Files & downloading

PDC files are the raw and processed artifacts of each study (mass spectra, search results, summary
reports, etc.). Three queries list files; one of them gives you a downloadable URL.

## The three file queries

| Query | Use | Signed URL? |
|---|---|---|
| `filesPerStudy(study_id, offset, limit)` | List a study's files **with a download link** | **Yes** — `signedUrl { url }` |
| `getPaginatedFiles(study_id, offset, limit)` | Paginated study file list (id/name/type/format/category/md5) | No |
| `fileMetadata(offset, limit)` | Rich per-file metadata across PDC, incl. `aliquots { case_submitter_id … }` | No |

All accept the extra filters `file_type`, `data_category`, `file_format`, `file_name` (and study-ID
variants). `fileMetadata`'s `limit` **cannot exceed 25000**. See [PAGINATION.md](PAGINATION.md).

```graphql
{ filesPerStudy(study_id: "0fe15489-1381-4864-8b17-6159e14a65a8" offset: 0 limit: 20)
  { file_id file_name file_type data_category file_format file_size md5sum signedUrl { url } } }
```

`filesPerStudy` is flagged *"may take a long time because of the huge volume of data"* — filter by
`data_category` / `file_type` and use small pages.

## Downloading

The `signedUrl.url` from `filesPerStudy` is a **pre-signed AWS S3 link** — fetch it with a plain HTTP
GET, no auth/headers:

```python
import requests
URL = "https://proteomic.datacommons.cancer.gov/graphql"
q = '{ filesPerStudy(study_id:"%s" offset:0 limit:1) { file_name file_size md5sum signedUrl { url } } }' % STUDY_ID
f = requests.post(URL, json={"query": q}).json()["data"]["filesPerStudy"][0]
with requests.get(f["signedUrl"]["url"], stream=True) as resp:
    resp.raise_for_status()
    with open(f["file_name"], "wb") as fh:
        for chunk in resp.iter_content(1 << 20):
            fh.write(chunk)
# verify f["md5sum"] against the downloaded file
```

### Two hard limits (no credentials involved)

- **Signed URLs expire after 7 days (168 hours).** Re-run `filesPerStudy` to mint a fresh URL; don't
  cache the URL itself.
- **Same file, same IP: 10 downloads / 24 hours.** Exceeding it returns an error from S3. Cache the
  downloaded bytes, not repeated downloads.

### Bulk downloads

For many/large files, PDC recommends the **PDC Data Download Client** (a command-line tool supporting
resumable transfers) driven by an exported **file manifest** from the portal, rather than looping
signed URLs. Mention this to users with large download sets. Clinical/biospecimen "downloads" from the
portal are manifest exports (CSV/TSV); via the API, fetch that data directly with the clinical queries
in [CLINICAL.md](CLINICAL.md).

## Data categories & file types

`data_category` examples: `Raw Mass Spectra`, `Processed Mass Spectra`, `Peptide Spectral Matches`,
`Protein Assembly`, `Quality Control`, `Supplementary Data`. `file_type` / `file_format` examples:
`Proprietary` / `vendor-specific` (raw vendor files), `Open Standard` / `mzML`, `Text` / `tsv`.

Use `filesCountPerStudy(pdc_study_id: …)` to see the count breakdown by `file_type` × `data_category`
before listing, so you can filter to just the category you need.

## Processed output formats (what's in the files)

PDC's Common Data Analysis Pipeline (CDAP) produces, per study:

- **Spectral library**, **PSM** (peptide-spectrum match) tables, **Protein Assembly** outputs.
- **Summary reports** — `*.summary.tsv` (identification, incl. spectral counts), and isobaric
  quantitation tables like `*.tmt11.tsv` carrying **Log Ratio** and **Unshared Log Ratio** columns
  (see [QUANTITATION.md](QUANTITATION.md)).
- **QC reports** and provider-submitted **supplementary data**.

Worked example: [examples/study_files_download.md](../examples/study_files_download.md).
