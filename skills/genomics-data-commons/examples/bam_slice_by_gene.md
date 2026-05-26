# Slice a BAM by gene name

The `/slicing/view/{file_id}` endpoint streams a BAM containing only the reads overlapping the
requested regions or gene(s). Gene names follow HGNC / GENCODE v36. Slicing controlled-access BAMs
requires an `X-Auth-Token`.

The sliced BAM has no `.bai` — index it locally with `samtools index`.

## Example

```python
import os, requests

token = os.environ["GDC_TOKEN"]
file_id = "a5b9acbd-adea-47d0-a3a3-3eb6ebfde56b"  # a harmonized BAM in the Portal

payload = {"gencode": ["BRCA1", "BRCA2"]}

r = requests.post(
    f"https://api.gdc.cancer.gov/slicing/view/{file_id}",
    headers={"Content-Type": "application/json",
             "X-Auth-Token": token},
    json=payload,
    stream=True,
)
r.raise_for_status()

with open("brca12.bam", "wb") as f:
    for chunk in r.iter_content(chunk_size=1 << 20):
        f.write(chunk)

# Index the slice so downstream tools (IGV, GATK, etc.) can use it.
import subprocess
subprocess.run(["samtools", "index", "brca12.bam"], check=True)
```

Region-based slicing uses the same shape:

```python
payload = {"regions": ["chr1", "chr2:10000", "chr3:10000-20000"]}
# or unmapped reads:
payload = {"regions": ["unmapped"]}
```

The GET form is also supported for short queries:

```bash
curl -H "X-Auth-Token: $GDC_TOKEN" \
  'https://api.gdc.cancer.gov/slicing/view/<file-uuid>?gencode=BRCA1' \
  --output brca1.bam
```
