# Gene & protein spectral counts across studies

`geneSpectralCount` and `protein` tell you which studies detected a gene/protein and with how much
peptide evidence. **Spectral counts are per analytical sample (a TMT/iTRAQ plex mixing several
biological samples) — identification evidence, not per-patient quantitation.** For relative abundance
per sample, use the quant matrix instead ([quant_matrix.md](quant_matrix.md)).

## Example

```python
import time, requests
from collections import Counter
URL = "https://proteomic.datacommons.cancer.gov/graphql"
def pdc(q, tries=5):                       # see quickstart.md — PDC emits transient null payloads
    for k in range(tries):
        b = requests.post(URL, json={"query": q}, timeout=180).json()
        if b.get("errors"): raise RuntimeError(b["errors"])
        data = b.get("data")
        if data and all(v is not None for v in data.values()): return data
        time.sleep(2 * (k + 1))
    raise RuntimeError("PDC returned null data after retries")

# geneSpectralCount returns a LIST of gene records (the name can match several genes).
# First call for a gene may be slow / time out due to data volume, then it's cached — retry.
genes = pdc('''{ geneSpectralCount(gene_name: "TP53")
                 { gene_name NCBI_gene_id chromosome
                   spectral_counts { pdc_study_id study_submitter_id plex spectral_count distinct_peptide unshared_peptide } } }''')["geneSpectralCount"]

gene = next(g for g in genes if g["gene_name"] == "TP53")   # filter to the exact symbol
print(gene["gene_name"], "NCBI", gene["NCBI_gene_id"], "chr", gene["chromosome"])

# Which studies detected it, and total spectral evidence per study?
per_study = Counter()
for sc in gene["spectral_counts"]:
    per_study[sc["pdc_study_id"]] += sc["spectral_count"]
for study, total in per_study.most_common(10):
    print(f"{study}  spectral_count={total}")
```

## From a protein accession

`protein` accepts a UniProt or RefSeq accession and resolves it to the gene before returning counts:

```python
prot = pdc('''{ protein(protein: "M0R009")
                { gene_name NCBI_gene_id
                  spectral_counts { project_submitter_id pdc_study_id plex spectral_count } } }''')["protein"]
# prot is a list of gene records as well; take the match.
```

## Finer granularity

- `aliquotSpectralCount(gene_name, dataset_alias)` — per-aliquot counts for one gene in one dataset.
- `paginatedSpectralCountPerStudyAliquot(study_id, plex_name, gene_name, offset, limit)` — counts per
  study/aliquot/gene, paginated.
- `getPaginatedGenes(gene_name)` — gene records (id, NCBI id, locus, mapped `proteins`, `assays`)
  without spectral counts; good for resolving a symbol to its `gene_id` / protein accessions.

## Notes

- Both `geneSpectralCount` and `protein` return a **list** — always filter to the exact `gene_name`
  rather than assuming `[0]`.
- `spectral_count` = total spectra; `distinct_peptide` / `unshared_peptide` distinguish all vs
  uniquely-mapped peptides (the same shared-vs-unshared distinction as log2 vs unshared-log2 ratios —
  see [../references/QUANTITATION.md](../references/QUANTITATION.md)).
