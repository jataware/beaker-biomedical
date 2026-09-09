# Pull a case with its full diagnoses list

The `/cases/{case_id}` endpoint returns scalar fields only by default. To get the nested clinical
data — diagnoses, demographic, samples, etc. — use the `expand` parameter. Each name in `expand`
must come from the `expand` list at `/cases/_mapping`.

## Example

```python
import requests

case_id = "1f601832-eee3-48fb-acf5-80c4a454f26e"   # TCGA-BH-A0EA

r = requests.get(
    f"https://api.gdc.cancer.gov/cases/{case_id}",
    params={
        "expand": "diagnoses,demographic,samples.portions.analytes.aliquots,exposures,follow_ups",
        "pretty": "true",
    },
)
r.raise_for_status()
case = r.json()["data"]

# Each diagnosis is a dict with ajcc_pathologic_stage, primary_diagnosis,
# days_to_last_follow_up, etc.
for dx in case.get("diagnoses", []):
    print(dx["primary_diagnosis"], dx.get("ajcc_pathologic_stage"),
          dx.get("age_at_diagnosis"))

# Walk biospecimen: case → samples → portions → analytes → aliquots
for sample in case.get("samples", []):
    print(sample["sample_type"], sample["submitter_id"])
    for portion in sample.get("portions", []):
        for analyte in portion.get("analytes", []):
            for aliquot in analyte.get("aliquots", []):
                print("  aliquot:", aliquot["aliquot_id"], aliquot["submitter_id"])
```
