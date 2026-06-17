# Worked: a live-API surprise → a new Critical rule

When there's no failing test yet — a user reports a weird result, or you're auditing — go to the API
and diff reality against the skill.

## 1. Probe

The skill lists `/genes` as "all annotated genes". A user got far fewer than expected. Check live:

```python
import requests
all_genes = requests.get("https://api.gdc.cancer.gov/genes", params={"size": 0}).json()
print(all_genes["data"]["pagination"]["total"])   # 22638
census = requests.post("https://api.gdc.cancer.gov/genes",
    json={"filters": {"op": "=", "content": {"field": "is_cancer_gene_census", "value": "true"}}, "size": 0}).json()
print(census["data"]["pagination"]["total"])       # 716
```

The Portal defaults to Cancer Gene Census (716), not all 22,638 — a large, silent cut the skill
never mentioned. That's the surprise.

## 2. Diagnose

Skill gap: a silent default that changes results by 30× and isn't stated. It's cross-cutting (it
hits `/genes`, `/ssms`, `/cnvs`, and the analysis endpoints, each with a *different* filter field).

## 3. & 4. Locate + edit

A **Critical rule** in `SKILL.md` (the default + the mandate to disclose it), and the per-endpoint
filter-field table in `references/ANALYSIS.md`. Bake in the verified counts:

```markdown
- **Cancer Gene Census is the default for gene-centric queries — and you must say so.** Mirror the
  Portal: filter on `is_cancer_gene_census = "true"` (the string, not a boolean) whenever you list,
  search, or aggregate genes/SSMs/CNVs, unless the user asks for the full universe. The cut is large
  and otherwise silent — `/genes` 22,638→716, `/ssms` 3.32M→218k — so tell the user every time. The
  filter field path differs per endpoint; see [references/ANALYSIS.md](references/ANALYSIS.md).
```

## 5. Re-verify + protect

There's no test for this yet, so the fix is unprotected against regression. Hand off to
`harness-test-author` to add `gdc:query_mechanics/...` covering "lists genes → applies census
default → discloses it" (a `behavior` for the disclosure, a `number` near 716). Then the next run of
the suite guards the rule.
