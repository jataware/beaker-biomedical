# Search files matching a project and data type

POST to the `/files` endpoint with an `and`-composed filter to find every file that belongs to a
project and matches a data-type constraint. Returns a TSV with the case barcode and biospecimen
context useful for downstream analysis.

## Example

```python
import requests, json

filters = {
    "op": "and",
    "content": [
        {"op": "in",
         "content": {"field": "cases.project.project_id",
                     "value": ["TCGA-BRCA"]}},
        {"op": "=",
         "content": {"field": "files.data_type",
                     "value": "Gene Expression Quantification"}},
        {"op": "=",
         "content": {"field": "files.access", "value": "open"}},
    ],
}

params = {
    "filters": filters,
    "fields": ",".join([
        "file_id",
        "file_name",
        "cases.submitter_id",
        "cases.case_id",
        "data_category",
        "data_type",
        "cases.samples.tumor_descriptor",
        "cases.samples.tissue_type",
        "cases.samples.sample_type",
        "cases.samples.submitter_id",
        "cases.samples.sample_id",
        "analysis.workflow_type",
        "cases.project.project_id",
        "cases.samples.portions.analytes.aliquots.aliquot_id",
        "cases.samples.portions.analytes.aliquots.submitter_id",
    ]),
    "format": "tsv",
    "size": "10000",
}

r = requests.post("https://api.gdc.cancer.gov/files",
                  headers={"Content-Type": "application/json"},
                  json=params)
r.raise_for_status()
open("tcga_brca_geneexp.tsv", "wb").write(r.content)
```
