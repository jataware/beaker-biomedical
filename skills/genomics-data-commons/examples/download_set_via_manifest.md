# Build a Data Transfer Tool manifest from a filter

For data volumes beyond what's reasonable to fetch through `/data` (think tens of GB+), the GDC
recommends piping a manifest into the `gdc-client` Data Transfer Tool. The manifest can be generated
directly from a `/files` query by appending `&return_type=manifest`.

## Example

```python
import json, requests, urllib.parse

filters = {
    "op": "and",
    "content": [
        {"op": "=", "content": {"field": "experimental_strategy", "value": ["RNA-Seq"]}},
        {"op": "=", "content": {"field": "cases.project.project_id", "value": ["TCGA-KIRC"]}},
        {"op": "=", "content": {"field": "cases.samples.sample_type",
                                "value": ["Solid Tissue Normal"]}},
    ],
}

url = "https://api.gdc.cancer.gov/files"
qs = urllib.parse.urlencode({
    "filters": json.dumps(filters),
    "return_type": "manifest",
})
r = requests.get(f"{url}?{qs}")
r.raise_for_status()
with open("gdc_manifest.txt", "wb") as f:
    f.write(r.content)
# Then on the shell:
#   gdc-client download -m gdc_manifest.txt           # open access
#   gdc-client download -m gdc_manifest.txt -t TOKEN  # controlled access
```
