# Protein quantitation matrix → DataFrame (with aliquot→case mapping)

`quantDataMatrix` returns a whole study's relative protein quantitation as a 2-D array. This example
fetches it, reshapes it into a genes × aliquots DataFrame, and maps the aliquot columns back to
patient cases.

Read [../references/QUANTITATION.md](../references/QUANTITATION.md) first — the values are **relative
log2 ratios against a common reference sample**, not absolute abundance, and reference/QC channels
appear as columns you'll want to drop.

## Example

```python
import time, requests, pandas as pd
URL = "https://proteomic.datacommons.cancer.gov/graphql"
def pdc(q, tries=5):                       # see quickstart.md — PDC emits transient null payloads
    for k in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=300).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        data = b.get("data")
        if data and all(v is not None for v in data.values()): return data
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

PDC_STUDY = "PDC000127"   # CPTAC CCRCC Discovery Study - Proteome

# 1. Fetch the matrix. Note the unusual syntax: the field takes NO sub-selection.
#    data_type: "log2_ratio" (all peptides) or "unshared_log2_ratio" (unique peptides only).
#    First call may be slow / time out, then it's cached — just retry.
matrix = pdc('{ quantDataMatrix(pdc_study_id: "%s" data_type: "log2_ratio") }' % PDC_STUDY)["quantDataMatrix"]

header = matrix[0]                      # ["Gene/Aliquot", "<aliquot_id>:<aliquot_submitter_id>", ...]
col_keys = header[1:]
rows = matrix[1:]                       # [["A1BG", "-0.12", ...], ...]

df = pd.DataFrame(
    [[pd.to_numeric(v, errors="coerce") for v in r[1:]] for r in rows],
    index=[r[0] for r in rows],         # gene_name
    columns=col_keys,
)
df.index.name = "gene"
print(df.shape)                         # (~genes, ~aliquots)

# 2. Split the composite column key "aliquot_id:aliquot_submitter_id".
aliquot_ids        = [c.split(":", 1)[0] for c in col_keys]
aliquot_submitters = [c.split(":", 1)[1] for c in col_keys]

# 3. Map aliquots -> cases via biospecimenPerStudy (flat aliquot/sample/case rows + sample_type).
bio = pdc('''{ biospecimenPerStudy(pdc_study_id: "%s")
              { aliquot_submitter_id case_submitter_id sample_type } }''' % PDC_STUDY)["biospecimenPerStudy"]
to_case   = {b["aliquot_submitter_id"]: b["case_submitter_id"] for b in bio}
to_sample = {b["aliquot_submitter_id"]: b["sample_type"]       for b in bio}

# 4. Keep only biological-sample columns. QC/reference channels DO appear in biospecimenPerStudy
#    (as pseudo-cases like "QC5" with a non-biological sample_type), so filter on sample_type — not
#    on "is it mapped". For PDC000127 the sample types are Primary Tumor / Solid Tissue Normal
#    (biological) vs Not Reported / Cell Lines (QC + the pooled reference). Verify the set per study.
BIOLOGICAL = {"Primary Tumor", "Solid Tissue Normal"}
bio_cols = [c for c, sub in zip(col_keys, aliquot_submitters)
            if to_sample.get(sub) in BIOLOGICAL]
df_bio = df[bio_cols]
df_bio.columns = pd.MultiIndex.from_tuples(
    [(to_case[c.split(":",1)[1]], to_sample[c.split(":",1)[1]], c.split(":",1)[1]) for c in bio_cols],
    names=["case", "sample_type", "aliquot"],
)
print(df_bio.iloc[:3, :3])
# e.g. column ("C3L-00791", "Primary Tumor", "CPT0026410003")

# Now df_bio is genes × (case, sample_type, aliquot) of log2 ratios, ready for analysis
# (e.g. tumor-vs-normal contrasts using the sample_type level).
```

## Notes

- **`data_type`:** `log2_ratio` vs `unshared_log2_ratio` — use unshared when protein-level specificity
  matters (homolog families), log2_ratio for coverage. An unavailable type raises
  `"Matrix data not found!"` — that usually means the study isn't an isobaric/TMT study; check its
  `experiment_type` via `study`.
- **No pagination / no cap.** The full matrix returns at once. For a large study the first call can be
  slow; raise the client timeout and retry (results are cached server-side).
- **Reference/QC columns** (pooled references, `QC*`, `NCI7-*`) are *present* in `biospecimenPerStudy`
  as pseudo-cases with a non-biological `sample_type` (e.g. `Not Reported`, `Cell Lines`) — so you
  can't drop them by "unmapped". Filter on `sample_type` (keep `Primary Tumor` / `Solid Tissue Normal`,
  etc.). Inspect the study's sample-type set first; it varies.
- To reproduce the Mean/Median/StdDev printed in the downloadable summary files, add each column's
  median back (PDC's file stats are computed *before* median normalization).
