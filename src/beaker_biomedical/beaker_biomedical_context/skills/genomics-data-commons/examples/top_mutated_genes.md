# Top mutated genes for a cohort — matching the GDC Data Portal

`POST /analysis/top_mutated_genes` ranks genes by the number of cases in a cohort with ≥1 simple
somatic mutation in that gene. To reproduce the GDC Data Portal's gene table **exactly**, use both
filter slots (they do different jobs) and apply the Cancer Gene Census default:

- **`case_filters` → the cohort / denominator** — `num_cohort_ssm_cases` = cohort cases *tested* for
  SSM (`available_variation_data = ssm`). Scope the cohort here, never in `filters`.
- **`filters` → the Cancer Gene Census default** — `genes.is_cancer_gene_census = "true"`, which
  decides *which* genes are eligible to appear. This is the Portal default; **apply it and tell the
  user**. Lift it only if they ask for all genes.

See [../references/MUTATION-FREQUENCY.md](../references/MUTATION-FREQUENCY.md#case_filters-vs-filters--and-the-frequency-denominator).

## Example — top mutated genes for kidney

```python
import io, csv, requests

# primary_site values are discoverable via a /cases facet; the kidney value is lowercase "kidney".
body = {
    "case_filters": {"op": "in", "content": {"field": "cases.primary_site", "value": ["kidney"]}},
    "filters":      {"op": "=",  "content": {"field": "genes.is_cancer_gene_census", "value": "true"}},
}
r = requests.post("https://api.gdc.cancer.gov/analysis/top_mutated_genes",
                  headers={"Content-Type": "application/json"}, json=body)
r.raise_for_status()

rows = list(csv.DictReader(io.StringIO(r.text), delimiter="\t"))
denom = rows[0]["num_cohort_ssm_cases"]          # 1035 — kidney cases tested for SSM
for row in rows[:7]:
    affected = int(row["num_cohort_ssm_affected_cases"])
    # cohort_ssm_affected_cases_percentage is already in percent units (e.g. 33.14).
    print(f"{row['symbol']:>7}  {affected:>3}/{denom}  ({row['cohort_ssm_affected_cases_percentage']}%)")
```

Output — matches the Portal 1:1 (current data release; exact counts drift between releases):

```
    VHL  343/1035  (33.14%)
  PBRM1  243/1035  (23.48%)
  MUC16   96/1035  (9.28%)
  SETD2   92/1035  (8.89%)
   BAP1   89/1035  (8.60%)
   TP53   61/1035  (5.89%)
   MTOR   58/1035  (5.60%)
```

Tell the user the list is Cancer-Gene-Census-only (the Portal default) and that the denominator (1035)
is the count of kidney cases tested for SSM.

## The census filter sets eligibility, not rank

Order is **always** by cohort mutation frequency; the census filter only changes *which* genes can
appear. Two consequences worth stating to users:

- **A famous census gene can rank low.** TP53 is in the census, but it's only the **6th** most-mutated
  gene in kidney (5.9%) — kidney is driven by VHL (33%) and PBRM1 (23%), and TP53 is a rare event in
  renal cell carcinoma (unlike ovarian/lung-squamous/colorectal, where TP53 is #1). Census membership
  does not promote it.
- **Large passenger-prone genes can rank high.** Drop the census `filters` clause and non-census TTN
  appears at #3 (19.3%) purely from its length; the census default removes it. MUC16 is the same kind
  of large, passenger-heavy gene but *is* flagged census, so it survives the filter and outranks TP53
  on raw case count — a mutation-burden artifact, not kidney biology.

## Other cohorts

Swap the `case_filters` field to scope differently — `cases.project.project_id` for a single project
(e.g. `["TCGA-KIRC"]`), `cases.disease_type`, or a saved `cohort_id` — and keep the census `filters`
clause for Portal parity. To rank SSMs *within* one gene use `/analysis/top_ssms_by_gene` (+ a
`gene_id`); to rank SSMs across the cohort regardless of gene use `/analysis/top_ssms`.
