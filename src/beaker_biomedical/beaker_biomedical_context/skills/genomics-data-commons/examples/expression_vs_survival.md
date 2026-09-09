# Gene expression vs. overall survival — matching the GDC Data Portal

The Portal's "Gene Expression" survival analysis (e.g. *does high MYC expression correlate with overall
survival in BRCA?*) is a three-step recipe, and the cutoff it shows is **not** arbitrary:

1. **Cohort** = a project/site cohort (here the **TCGA-BRCA project**, which is what the Portal's "BRCA"
   resolves to for clinical survival).
2. **Cutoff** = the **median of the gene's raw `uqfpkm`** across the cohort. The Portal's default split is
   the median (two groups, `< cutoff` and `≥ cutoff`); cases with no expression data become the
   **"Missing data"** group and are excluded from the comparison. For MYC in TCGA-BRCA the median is
   **16.24 uqFPKM** — that is exactly the cutoff the Portal displays.
3. **Survival** = `/analysis/survival` with **both groups passed as an array** so it runs the log-rank
   test and returns `overallStats.pValue`.

**Tell the user the cutoff is the cohort-median uqFPKM (the Portal default).** They can instead bin by
quartiles or a custom value — just change how you partition the case IDs in step 2.

## Full recipe

```python
import io, csv, statistics, requests

GENE = "ENSG00000136997"          # MYC
COHORT = {"op": "in", "content": {"field": "cases.project.project_id", "value": ["TCGA-BRCA"]}}

# 1+2. Pull raw uqFPKM for the gene across the cohort, then split at the median.
exp = requests.post(
    "https://api.gdc.cancer.gov/gene_expression/values",
    headers={"Content-Type": "application/json", "Accept": "text/tab-separated-values"},
    json={"case_filters": COHORT, "gene_ids": [GENE], "tsv_units": "uqfpkm", "format": "tsv"},
)
exp.raise_for_status()
reader = csv.reader(io.StringIO(exp.text), delimiter="\t")
case_ids = next(reader)[1:]                      # header: gene_id, <case uuids...>
values   = [float(v) for v in next(reader)[1:]]  # the gene's row

cutoff = statistics.median(values)               # 16.24 for MYC/TCGA-BRCA
low  = [c for c, v in zip(case_ids, values) if v <  cutoff]   # "< cutoff" group
high = [c for c, v in zip(case_ids, values) if v >= cutoff]   # "≥ cutoff" group
# cases NOT in case_ids (no expression data) = the Portal's "Missing data" group; omit from the test.

# 3. Two-group survival in ONE call (array of filters) → log-rank p-value.
def grp(ids): return {"op": "in", "content": {"field": "cases.case_id", "value": ids}}
surv = requests.post(
    "https://api.gdc.cancer.gov/analysis/survival",
    headers={"Content-Type": "application/json"},
    json={"filters": [grp(low), grp(high)]},      # array → multiple curves + overallStats
).json()

print(f"cutoff (median uqFPKM) = {cutoff:.2f}")
print("log-rank:", surv["overallStats"])          # {chiSquared, degreesFreedom, pValue}
for label, curve in zip(["< cutoff", "≥ cutoff"], surv["results"]):
    donors = curve["donors"]                       # time(days), censored, survivalEstimate
    print(f"  {label}: n={len(donors)}")
    # Kaplan-Meier:
    # from lifelines import KaplanMeierFitter
    # KaplanMeierFitter().fit([d["time"] for d in donors],
    #                         event_observed=[not d["censored"] for d in donors]).plot()
```

## Validated output (current release; values drift between releases)

```
cutoff (median uqFPKM) = 16.24
log-rank: {'chiSquared': 2.58, 'degreesFreedom': 1, 'pValue': 0.108}
  < cutoff: n=533        # 547 cases below median, 14 dropped for missing survival time
  ≥ cutoff: n=540        # 548 cases at/above median, 8 dropped
```

1095 TCGA-BRCA cases have MYC expression; the median split is 547 / 548. `/analysis/survival` drops
cases with no follow-up time, so the plotted curves hold fewer donors than the split — report both
counts. The log-rank `pValue` (0.108) is the number behind the Portal's "Group comparisons" table; here
it says MYC expression is **not** significantly associated with overall survival in TCGA-BRCA (p > 0.05).

## Key points to carry over

- **The cutoff is the cohort median of raw `uqfpkm`** — fetch with `tsv_units=uqfpkm`, not the log2 units.
  (Don't confuse the value with a log2 number; MYC's median is ~16 uqFPKM, not a log2 figure.)
- **Pass groups as an array** to `/analysis/survival`. A single filter object returns one curve and an
  **empty** `overallStats` (no p-value) — see [../references/ANALYSIS.md](../references/ANALYSIS.md#survival).
- **"Missing data" = cases without expression**, reported by the Portal as a third group but left out of
  the pairwise log-rank test.
- To bin differently (quartiles, top vs bottom tertile, a literal threshold), change only the
  partition in step 2; steps 1 and 3 are unchanged.
