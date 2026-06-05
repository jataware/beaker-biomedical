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
`data_category` / `file_type` and use small pages. Get those filter values from `filesCountPerStudy`
first; a guessed value silently returns nothing (see the footgun below).

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

## Data categories & file types — discover them, don't guess (FOOTGUN)

`data_category`, `file_type`, and `file_format` are **controlled vocabularies**. Passing a value that
isn't an exact PDC enum string returns an **empty list with no `errors`** (HTTP 200) — it looks
identical to "this study has no such files." A plausible-but-wrong guess like
`data_category: "Protein Report"` therefore silently yields zero rows and can mislead you into
reporting "no files" when the real category was `"Protein Assembly"`.

**Always enumerate the study's actual categories first** with `filesCountPerStudy`, then filter
`filesPerStudy`/`getPaginatedFiles` using a value taken verbatim from that result — never a value you
assumed:

```graphql
{ filesCountPerStudy(pdc_study_id: "PDC000127") { data_category file_type files_count } }
```

```python
# pick the category programmatically instead of hardcoding a literal
counts = pdc('{ filesCountPerStudy(pdc_study_id:"%s") { data_category file_type files_count } }' % PDC_STUDY)["filesCountPerStudy"]
categories = sorted({c["data_category"] for c in counts})   # the ONLY valid values for this study
# e.g. choose "Protein Assembly" (processed protein report) from `categories`, then filter filesPerStudy
```

Values seen in PDC are things like `Raw Mass Spectra`, `Peptide Spectral Matches`, `Protein Assembly`
(file types `Proprietary`/`Open Standard`/`Text`; formats `vendor-specific`/`mzML`/`tsv`) — but
**treat any such list as illustrative only**; the authoritative, currently-valid set for a given study
is whatever `filesCountPerStudy` returns. If a filtered `filesPerStudy` call comes back empty, re-check
the `data_category`/`file_type` spelling against `filesCountPerStudy` before concluding there are no
files. (Same principle for `disease_type` / `experiment_type` / `analytical_fraction` /
`tissue_or_organ_of_origin` — see [DISCOVERY.md](DISCOVERY.md).)

## Processed output formats (what's in the files)

PDC's Common Data Analysis Pipeline (CDAP) produces, per study:

- **Spectral library**, **PSM** (peptide-spectrum match) tables, **Protein Assembly** outputs.
- **Summary reports** — `*.summary.tsv` (identification, incl. spectral counts), and isobaric
  quantitation tables like `*.tmt11.tsv` carrying **Log Ratio** and **Unshared Log Ratio** columns
  (see [QUANTITATION.md](QUANTITATION.md)).
- **QC reports** and provider-submitted **supplementary data**.

Worked example: [examples/study_files_download.md](../examples/study_files_download.md).
