# Get a gene expression matrix (FPKM-UQ)

Pull a TSV matrix of normalized expression values (rows = genes, columns = cases) for a list of cases
and a list of Ensembl gene IDs. The response is median-centered log2(FPKM-UQ+1) — the same units the
Portal uses for heatmaps.

Server-side cap: 120 000 data points (genes × cases). Slice your request if you hit it.

## Example

```python
import io, csv, requests

payload = {
    "case_ids": [
        "6d4f38db-a97b-4dc0-8dc5-2ac7f2cc5e38",
        "e3b32485-b204-43a7-93a5-601408fcdf96",
        "000ead0d-abf5-4606-be04-1ea31b999840",
        "001ab32d-f924-4753-ad67-4366fb845ae6",
    ],
    "gene_ids": [
        "ENSG00000141510",   # TP53
        "ENSG00000181143",   # MUC16
    ],
    "tsv_units": "median_centered_log2_uqfpkm",
    "format": "tsv",
}

r = requests.post(
    "https://api.gdc.cancer.gov/gene_expression/values",
    headers={"Content-Type": "application/json",
             "Accept": "text/tab-separated-values"},
    json=payload,
)
r.raise_for_status()

reader = csv.reader(io.StringIO(r.text), delimiter="\t")
header = next(reader)              # ['gene_id', case_uuid_1, case_uuid_2, ...]
rows = list(reader)                # [['ENSG00000141510', '-0.58', '1.76', ...], ...]
print(header)
for row in rows:
    print(row[0], row[1:])

# Optional sanity check first — which inputs have data?
avail = requests.post(
    "https://api.gdc.cancer.gov/gene_expression/availability",
    headers={"Content-Type": "application/json"},
    json={"case_ids": payload["case_ids"], "gene_ids": payload["gene_ids"]},
).json()
print("cases with expression:", avail["cases"]["with_gene_expression_count"])
```
