# List a study's files and download one

`filesPerStudy` is the only query that returns a `signedUrl` — a pre-signed AWS S3 link you can GET
directly with no auth. See [../references/FILES.md](../references/FILES.md) for data categories, the
7-day URL expiry, and the 10-downloads/file/IP/24h limit.

## Example

```python
import time, requests, hashlib
URL = "https://proteomic.datacommons.cancer.gov/graphql"
def pdc(q, tries=5):                       # see quickstart.md — PDC emits transient null payloads
    for k in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=300).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        data = b.get("data")
        if data and all(v is not None for v in data.values()): return data
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

# filesPerStudy needs study_id (the version-specific UUID). Resolve the latest version first.
PDC_STUDY = "PDC000127"
cat = pdc('{ studyCatalog(pdc_study_id: "%s") { versions { study_id is_latest_version } } }' % PDC_STUDY)
study_id = next(v["study_id"] for v in cat["studyCatalog"][0]["versions"]
                if v["is_latest_version"] == "yes")

# 1. Discover this study's ACTUAL data_category values — don't guess them. data_category is a
#    controlled vocabulary; a wrong value (e.g. "Protein Report") returns an empty list with NO error.
counts = pdc('{ filesCountPerStudy(pdc_study_id: "%s") { file_type data_category files_count } }' % PDC_STUDY)["filesCountPerStudy"]
categories = sorted({c["data_category"] for c in counts})
for c in counts:
    print(c["data_category"], "/", c["file_type"], "=", c["files_count"])
print("valid data_category values for this study:", categories)

# 2. Pick a category FROM that list (here: the processed protein report = "Protein Assembly"),
#    matching against the real values instead of hard-coding a literal that might not exist.
want = next((cat for cat in categories if "Protein" in cat), categories[0])   # -> "Protein Assembly"
q = '''{ filesPerStudy(study_id: "%s" data_category: "%s" offset: 0 limit: 10)
         { file_id file_name file_type file_size md5sum signedUrl { url } } }''' % (study_id, want)
files = pdc(q)["filesPerStudy"]
print(f"{len(files)} {want!r} files")
assert files, f"empty result — re-check data_category against {categories}"   # empty != necessarily none

# 3. Download one and verify its checksum.
f = files[0]
with requests.get(f["signedUrl"]["url"], stream=True, timeout=600) as resp:
    resp.raise_for_status()                     # the S3 URL needs no auth headers
    md5 = hashlib.md5()
    with open(f["file_name"], "wb") as fh:
        for chunk in resp.iter_content(1 << 20):
            fh.write(chunk); md5.update(chunk)
assert md5.hexdigest() == f["md5sum"], "checksum mismatch"
print("downloaded + verified:", f["file_name"], f["file_size"], "bytes")
```

## Notes

- **Signed URLs expire after 7 days.** Don't persist the URL — re-run `filesPerStudy` to mint a fresh
  one. The same file from the same IP is capped at 10 downloads / 24h.
- **`data_category` / `file_type` are controlled vocabularies — a wrong value returns `[]` with no
  error, not a 400.** So an empty result might just mean a mistyped/guessed category. Get the valid
  values for the study from `filesCountPerStudy` (step 1) and filter with one of those, exactly. See
  [../references/FILES.md](../references/FILES.md).
- **`filesPerStudy` can be slow** on big studies (it's flagged "huge volume of data"). Filter by a
  discovered `data_category` / `file_type` and page with small `limit`s.
- For many/large files, point the user at the **PDC Data Download Client** (resumable, manifest-driven)
  rather than looping signed URLs in Python.
- Need per-file metadata with case linkage instead of a download? Use `fileMetadata` — it returns
  `aliquots { case_submitter_id … }` (no signed URL). `getPaginatedFiles` is the paginated list
  without URLs.
