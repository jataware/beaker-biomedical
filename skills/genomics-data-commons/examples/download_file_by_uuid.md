# Download files by UUID

Single-file download is a `GET /data/{uuid}`. Multi-file download is `POST /data` with a list of
UUIDs and returns a `.tar.gz` archive. Both paths honor `X-Auth-Token` for controlled-access data.

## Example

```python
import os, re, requests

# --- Single open-access file ---
file_id = "a68e75c8-0e01-446b-86b8-09b6903fa409"
r = requests.get(f"https://api.gdc.cancer.gov/data/{file_id}")
r.raise_for_status()
filename = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
with open(filename, "wb") as f:
    f.write(r.content)

# --- Multiple files in one tar.gz ---
ids = [
    "a68e75c8-0e01-446b-86b8-09b6903fa409",
    "649e1e0e-b4ce-491c-94c3-64273680159b",
]
r = requests.post(
    "https://api.gdc.cancer.gov/data",
    headers={"Content-Type": "application/json"},
    json={"ids": ids},
)
r.raise_for_status()
filename = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
with open(filename, "wb") as f:
    f.write(r.content)

# --- Controlled-access (BAM with companion BAI) ---
token = os.environ["GDC_TOKEN"]
bam_id = "f587ef82-acbe-44f9-ad5a-6207e148f61f"
r = requests.get(
    f"https://api.gdc.cancer.gov/data/{bam_id}",
    headers={"X-Auth-Token": token},
    params={"related_files": "true"},  # also pull the .bai
    stream=True,
)
r.raise_for_status()
filename = re.findall("filename=(.+)", r.headers["Content-Disposition"])[0]
with open(filename, "wb") as f:
    for chunk in r.iter_content(chunk_size=1 << 20):
        f.write(chunk)
```
