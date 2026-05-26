# Survival data for a cohort

`/analysis/survival` returns the raw per-donor points behind the survival plots in the GDC Data
Portal: time-to-event and a censoring flag, optionally stratified by a categorical field. Plug the
result into a Kaplan-Meier library to render.

## Example

```python
import json, requests, urllib.parse

# Cohort: TCGA-BRCA cases stratified by ER status
filters = {
    "op": "and",
    "content": [
        {"op": "in",
         "content": {"field": "cases.project.project_id",
                     "value": ["TCGA-BRCA"]}},
    ],
}

qs = urllib.parse.urlencode({"filters": json.dumps(filters)})
r = requests.get(f"https://api.gdc.cancer.gov/analysis/survival?{qs}")
r.raise_for_status()
result = r.json()

# Each `result` block carries a donors[] list with time, censored, survivalEstimate
for strata in result["results"]:
    donors = strata["donors"]
    times = [d["time"] for d in donors]
    censored = [d["censored"] for d in donors]
    # Hand off to lifelines:
    # from lifelines import KaplanMeierFitter
    # KaplanMeierFitter().fit(times, event_observed=[not c for c in censored]).plot()
    print("strata:", strata["meta"]["id"], "n=", len(donors))
```

`time` is days from the index date (case.index_date — typically "Diagnosis" or "Sample
Procurement"). `censored=true` means the patient was alive at last contact (right-censored).
