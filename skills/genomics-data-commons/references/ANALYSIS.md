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

## Cancer Gene Census default — applies across gene-centric endpoints

Mirror the GDC Data Portal: when you **list, search, or aggregate** genes / SSMs / CNVs, default to
filtering on the Cancer Gene Census (`is_cancer_gene_census = "true"`) and **tell the user you did**.
The portal shows only the ~716 COSMIC census genes by default rather than all ~22,600 annotated genes;
applying the same default here is least-surprising, but the silent cut is large — so the notice is
mandatory, not optional.

| Endpoint(s) | Census filter field | Census-only / unfiltered |
|---|---|---|
| `/genes` | `is_cancer_gene_census` | 716 / 22,638 |
| `/ssms` | `consequence.transcript.gene.is_cancer_gene_census` | 217,880 / 3,324,495 |
| `/ssm_occurrences` | `ssm.consequence.transcript.gene.is_cancer_gene_census` | occurrence-level; same field |
| `/cnvs` | `consequence.gene.is_cancer_gene_census` | 2,669 / 75,412 |
| `/cnv_occurrences` | `cnv.consequence.gene.is_cancer_gene_census` | occurrence-level; same field |
| `/analysis/top_mutated_genes`, `top_ssms`, `top_ssms_by_gene`, `top_ssms_by_case` | `genes.is_cancer_gene_census` | TSV |

- **This is a Portal convention, not an API default.** The API applies *no* implicit census filter
  anywhere — a bare query returns the full set (e.g. `/genes` → 22,638, not 716). The default lives in
  the GDC Data Portal's frontend, so nothing in the API response reveals that you added the filter;
  that's exactly why telling the user is mandatory.
- **The field path differs per endpoint** (above) — it is *not* `genes.is_cancer_gene_census`
  everywhere. That path is valid only on the mutation-frequency `/analysis/...` TSV endpoints; on
  `/ssms`/`/cnvs` the gene hangs off the consequence, and on `/genes` it's top-level. Confirm with
  `<endpoint>/_mapping` when unsure (this skill's "do not invent fields" rule applies). Note the trap:
  `is_cancer_gene_census` appears in `/genes/_mapping`'s `defaults` list, but `defaults` is the default
  *returned-field projection* (columns you get when you omit `fields=`), **not** a default filter.
- The value is the **string** `"true"` (or `"false"` for non-census only), never a JSON boolean.
- `and` the census clause with the user's own filters:
  `{"op":"and","content":[CENSUS, {...user filter...}]}`.
- **Skip the default and the notice** only when the user already constrained `is_cancer_gene_census`,
  or explicitly asked for the full gene universe / non-census genes.
- **Excluded:** `/genes/{gene_id}` (single-gene lookup — no filtering applies), and `/cases` / `/files`
  (the flag is absent from their `_mapping`).

```python
import requests
# /ssms, census-only — capture the total so you can report the cut you applied
F = {"op": "=", "content": {"field": "consequence.transcript.gene.is_cancer_gene_census", "value": "true"}}
r = requests.post("https://api.gdc.cancer.gov/ssms", json={"filters": F, "size": 0})
print(r.json()["data"]["pagination"]["total"])   # 217,880 census SSMs, vs 3,324,495 unfiltered
```

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

Single gene by Ensembl ID (no filtering — returns exactly that gene):

```bash
curl 'https://api.gdc.cancer.gov/genes/ENSG00000084073?pretty=true'
```

Returns: `gene_id`, `symbol`, `description`, `cytoband[]`, `gene_chromosome`, `gene_start`,
`gene_end`, `gene_strand`, `synonyms[]`, `biotype`, `canonical_transcript_*`, `is_cancer_gene_census`,
`is_oncogene`, `is_tumor_suppressor_gene`.

When you *list or search* `/genes` (as opposed to a single `/genes/{gene_id}` lookup), default to
`is_cancer_gene_census = "true"` and **tell the user you applied that default** — without it a bare
`/genes` list returns ~22,638 genes, vs 716 in the census. This is one instance of the cross-endpoint
default documented above in
[Cancer Gene Census default](#cancer-gene-census-default--applies-across-gene-centric-endpoints);
the filter field is top-level `is_cancer_gene_census` on this endpoint.
