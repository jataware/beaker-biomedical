# Protein quantitation

PDC's reason for existing is harmonized, mass-spectrometry-based protein quantitation. Understanding
*what the numbers mean* matters as much as fetching them.

## How PDC quantitation works (read this before interpreting values)

Most PDC studies (CPTAC and others) use an **isobaric labeling** workflow (TMT-*n* for n = 10, 11,
16, 18; or iTRAQ 4-plex). Multiple biological samples are each tagged with an isobaric reagent and
mixed into one **analytical sample**, then run together by tandem MS. Because raw peptide-ion
intensities are not comparable across peptides, every tag's intensity is **normalized against one tag
per spectrum**. To scale beyond a single plex's channel count, CPTAC includes a **common reference
sample** in every plex and uses its channel as the ratio denominator throughout — so a study's values
are all relative to that shared reference.

Consequences you must respect:

- **Values are relative log2 ratios, not absolute abundance.** PDC deliberately does not provide
  absolute protein abundance — only relative quantitation between samples. Don't describe a
  quant-matrix value as "the amount of protein."
- **A plex of capacity *n* carries *n−1* biological samples** (one channel is the reference). Reference
  / QC channels (e.g. labels named like `QC*`, `NCI7-*`, pooled references) appear as matrix columns
  too — exclude them for biological analysis.
- **Summary stats (Mean/Median/StdDev) in downloadable files are computed *before* median
  normalization** of the log2-ratio values. To reproduce them, add the per-column median back.

## `quantDataMatrix` — the matrix query

```graphql
{ quantDataMatrix(pdc_study_id: "PDC000127" data_type: "log2_ratio") }
```

Note the **unusual syntax**: the field takes no sub-selection (`{}`). The response is a 2-D array
under `data`:

```json
{ "data": { "quantDataMatrix": [
  ["Gene/Aliquot", "008202d2-...:CPT0026410003", "00b60c96-...:CPT0002370001", "01fb1ceb-...:QC5", ...],
  ["A1BG",          "-0.12",                       "0.44",                       "0.03",            ...],
  ["A2M",           "1.07",                        "-0.88",                      "0.10",            ...]
] } }
```

- **Row 0 is the header.** Cell 0 is the literal `"Gene/Aliquot"`; the rest are column keys of the form
  `aliquot_id:aliquot_submitter_id`.
- **Each later row** is `[gene_name, value, value, …]`.
- Values are strings; cast to float, and expect missing/blank cells.
- **No pagination.** The whole matrix returns at once — a proteome study is genes × ~100–200 aliquots,
  so the first call can be slow or time out (then it's cached and fast on retry). The only way to make
  it smaller is to pick a smaller study or a sparser analytical fraction.

### `data_type` values

| `data_type` | Meaning |
|---|---|
| `log2_ratio` | Relative protein abundance from **all** peptides mapping to the protein. |
| `unshared_log2_ratio` | Same, but **only uniquely-mapped (unshared) peptides** — excludes peptides shared between homologous proteins. |

These two are the documented options. Other workflow-dependent types exist (e.g. precursor-area /
spectral-count matrices for label-free studies). Availability depends on the study's analytical
workflow; **an unavailable `data_type` returns a GraphQL error `"Matrix data not found! pdc_study_id:
… : <type>"`** rather than an empty matrix. If `log2_ratio` errors, the study likely isn't an isobaric
study — check `study`/`protocolPerStudy` for its `experiment_type`.

### Log ratio vs. unshared log ratio (which to use)

- **Log ratio** can be a convolution of two homologous proteins' values (shared peptides counted for
  both). **Unshared log ratio** is cleaner but summarizes fewer peptides (noisier for some proteins).
- They usually agree closely. Use `unshared_log2_ratio` when protein-level specificity matters
  (homolog families); use `log2_ratio` for broader coverage. Say which one you used.

### Mapping matrix columns back to cases

The column key `aliquot_id:aliquot_submitter_id` is an **aliquot**, not a patient. To get to the
patient, resolve aliquot → sample → case with `biospecimenPerStudy` (flat rows of
`aliquot_id sample_id case_id aliquot_submitter_id … case_submitter_id`) or
`paginatedCasesSamplesAliquots`. See [examples/quant_matrix.md](../examples/quant_matrix.md).

## Spectral counts

`geneSpectralCount`, `aliquotSpectralCount`, `paginatedSpectralCountPerStudyAliquot`, and `protein`
return spectral counts: `spectral_count`, `distinct_peptide`, `unshared_peptide` per
project/plex/study.

- **Spectral counts are per analytical sample (plex), which mixes multiple biological samples.** They
  are *identification evidence*, not per-patient quantitation. Don't present a spectral count as a
  per-case measurement.
- `geneSpectralCount(gene_name: "A1BG")` aggregates a gene's counts across all studies; `protein(protein:
  "<UniProt/RefSeq>")` does the same starting from a protein accession (it maps to the gene first).
- `aliquotSpectralCount` and `paginatedSpectralCountPerStudyAliquot` go down to individual aliquots/plexes.

## Genes & proteins

- `getPaginatedGenes(gene_name: "TP53")` does a prefix/substring match — `TP53` returns `TP53`,
  `TP53AIP1`, `TP53BP1`, etc. Filter to the exact `gene_name` you want.
- A gene record carries `proteins` (mapped protein accessions) and `assays`.
- `protein` accepts UniProt or RefSeq accessions and resolves to the gene.
