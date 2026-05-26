# Analysis endpoints

A second family of read endpoints, structured the same way as `/files` and `/cases` — they accept
`filters`, `fields`, `size`, `from`, `sort`, `facets`, `format`, `expand`, `pretty`.

| Endpoint | Entity |
|---|---|
| `/genes`, `/genes/{gene_id}` | Genes (keyed by Ensembl ID, e.g. `ENSG00000084073`) |
| `/ssms`, `/ssms/{ssm_id}` | Simple somatic mutations (e.g. `chr1:g.52000C>T`) |
| `/ssm_occurrences`, `/ssm_occurrences/{id}` | SSMs joined to cases (one row per case carrying that SSM) |
| `/cnvs`, `/cnvs/{cnv_id}`, `/cnvs/ids` | Gene-level copy-number variation |
| `/cnv_occurrences`, `/cnv_occurrences/{id}`, `/cnv_occurrences/ids` | CNVs joined to cases |
| `/segment_cnvs`, `/segment_cnv_occurrences` | Segment-level CNVs |

Each supports `/_mapping` for field discovery.

## SSMs and observations

`/ssms` carries a row per distinct mutation. Use `expand=occurrence.case.observation.read_depth` to
surface MAF-style read-depth info per case:

```bash
curl 'https://api.gdc.cancer.gov/ssms/57bb3f2e-ec05-52c2-ab02-7065b7d24849?expand=occurrence.case.observation.read_depth&pretty=true'
```

Response includes `mutation_subtype`, `genomic_dna_change`, `gene_aa_change[]`, `chromosome`,
`start_position`/`end_position`, `reference_allele`/`tumor_allele`, `ncbi_build`, `cosmic_id`, and
the expanded `occurrence` array.

`observation` is not a top-level endpoint — it's only reachable via `expand` on `ssms` or
`ssm_occurrences`.

## CNVs

`/cnvs` returns gene-level CNV calls (Gain / Loss). `/cnvs/ids?query=<cnv_id>` is a typeahead-style
lookup that returns the parent nodes containing a CNV id.

## `/analysis/top_*` count endpoints

Four endpoints under `/analysis` produce JSON-shaped counts (as opposed to the TSV-producing
`/analysis/top_mutated_genes` family — see [MUTATION-FREQUENCY.md](MUTATION-FREQUENCY.md)):

| Endpoint | Returns |
|---|---|
| `/analysis/top_cases_counts_by_genes` | Per-project case counts for a gene list. **Does not** accept `format` or `fields`. |
| `/analysis/top_mutated_genes_by_project` | Most-mutated genes within a project |
| `/analysis/top_mutated_cases_by_gene` | Cases most affected by mutations in a given set of genes |
| `/analysis/mutated_cases_count_by_project` | Per-project counts of cases with any SSM (`case_with_ssm.doc_count`) |

## Survival

`/analysis/survival` returns the raw points behind the survival plot widget in the Portal. Pass
`filters` defining the cohort (and optional sub-stratifications).

```bash
curl 'https://api.gdc.cancer.gov/analysis/survival?filters=%7B...%7D'
```

Response shape:

```json
{
  "results": [
    {
      "donors": [
        {"id": "case-uuid", "submitter_id": "TCGA-...",
         "time": 1234, "censored": false, "survivalEstimate": 0.98}
      ],
      "meta": {"id": <hash>},
      "id": <strata-key>
    }
  ],
  "overallStats": {"...": "..."}
}
```

- `time` is days from index.
- `censored=true` means the patient was alive at last follow-up (right-censored).
- For Kaplan-Meier plotting, group donors by strata and feed into your KM library of choice.

## Genes endpoint quick reference

```bash
curl 'https://api.gdc.cancer.gov/genes/ENSG00000084073?pretty=true'
```

Returns: `gene_id`, `symbol`, `description`, `cytoband[]`, `gene_chromosome`, `gene_start`,
`gene_end`, `gene_strand`, `synonyms[]`, `biotype`, `canonical_transcript_*`, `is_cancer_gene_census`,
`is_oncogene`, `is_tumor_suppressor_gene`.
