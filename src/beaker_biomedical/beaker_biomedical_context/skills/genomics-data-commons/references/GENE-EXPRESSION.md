# Gene Expression API

Three endpoints under `https://api.gdc.cancer.gov/gene_expression/`:

| Endpoint | What it returns |
|---|---|
| `POST /availability` | Per-case and per-gene booleans: does FPKM-UQ data exist? |
| `POST /values` | TSV expression matrix (genes × cases) |
| `POST /gene_selection` | Top-N most variable genes for a case collection |

Genes are identified by Ensembl gene IDs matching `^ENSG\d{11}$`. **Only protein-coding genes** have
expression data — non-coding IDs return `has_gene_expression_values: false`.

## Case collections

All three endpoints define the case set using **exactly one** of:

- `case_ids` — list of case UUIDs.
- `case_set_id` — a GDC case-set identifier.
- `cohort_id` — a saved cohort (from the Cohort API).
- `case_filters` — a GDC `filters` JSON document (same shape as `/cases` filters).

Mixing these is a 400. The error message is literally:
`case_ids, case_set_id, cohort_id, and case_filters cannot be used together.`

## Gene collections

Same pattern with **exactly one** of:

- `gene_ids` — list of `ENSG...` IDs.
- `gene_set_id` — a GDC gene-set identifier.
- (For `/gene_selection` only) `gene_type` — the only legal value is `protein_coding`.

## `/availability`

```bash
curl -X POST 'https://api.gdc.cancer.gov/gene_expression/availability' \
  -H 'Content-Type: application/json' \
  -d '{
    "case_ids": ["6d4f38db-a97b-4dc0-8dc5-2ac7f2cc5e38",
                 "e3b32485-b204-43a7-93a5-601408fcdf96"],
    "gene_ids": ["ENSG00000141510", "ENSG00000181143"]
  }'
```

Response:

```json
{
  "cases": {
    "with_gene_expression_count": 1,
    "without_gene_expression_count": 1,
    "details": [
      {"case_id":"...","has_gene_expression_values": true},
      {"case_id":"...","has_gene_expression_values": false}
    ]
  },
  "genes": {
    "with_gene_expression_count": 2,
    "without_gene_expression_count": 0,
    "details": [
      {"gene_id":"ENSG00000141510","has_gene_expression_values": true},
      {"gene_id":"ENSG00000181143","has_gene_expression_values": true}
    ]
  }
}
```

Use this as a pre-flight check before calling `/values` — it tells you which inputs will yield
columns/rows.

## `/values`

```bash
curl -X POST 'https://api.gdc.cancer.gov/gene_expression/values' \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/tab-separated-values' \
  -d '{
    "case_ids": ["6d4f38db-a97b-4dc0-8dc5-2ac7f2cc5e38",
                 "e3b32485-b204-43a7-93a5-601408fcdf96"],
    "gene_ids": ["ENSG00000141510","ENSG00000181143"],
    "tsv_units": "median_centered_log2_uqfpkm",
    "format": "tsv"
  }'
```

Response is a TSV — first column `gene_id`, subsequent columns are case UUIDs:

```
gene_id  case-uuid-1  case-uuid-2  case-uuid-3
ENSG00000141510  -0.58248  1.75830  0.00000
ENSG00000181143  -0.02529  0.00000  3.52293
```

### Required and optional fields

| Field | Required | Notes |
|---|---|---|
| case collection (`case_ids`/`case_set_id`/`cohort_id`/`case_filters`) | yes (exactly one) | |
| gene collection (`gene_ids`/`gene_set_id`) | yes (exactly one) | |
| `tsv_units` | optional | `uqfpkm` (FPKM-UQ values) or `median_centered_log2_uqfpkm`. |
| `format` | optional | `tsv` (default) or `json`. JSON is currently **disabled server-side** — `format=json` returns an error. |

### `median_centered_log2_uqfpkm` calculation

1. For each (case, gene) compute `log2(uqfpkm + 1)`.
2. Take the median of those values across the matrix.
3. Subtract the median from each value.

This is useful for heatmaps where you want to plot deviation from a cohort mean.

### Hard limits

- **120 000 data-point cap** (cases × genes). Above that the server returns 400. Slice your query.
- Both `cases` and `genes` collections must be provided. `/values` does not accept cases-only or
  genes-only — that returns `Both cases and genes are required.`

## `/gene_selection`

Picks the top-N most variably expressed genes (by stddev of `log2(uqfpkm+1)`) within a cohort, filtered
to those with median expression above `min_median_log2_uqfpkm` (default 1).

**This is the endpoint for "what genes are highly/most expressed in \<cancer\>?"** — the GDC Data
Portal answers that question with the most *variably* expressed genes, **not** the highest absolute or
median level (which is dominated by uninformative housekeeping genes). Rank by variability here, and
**tell the user** you did so. For breast cancer this returns `SCGB2A2` as the #1 gene, matching the
Portal 1:1. Full worked recipe (incl. the absolute-level fallback):
[../examples/most_variable_genes.md](../examples/most_variable_genes.md).

```bash
curl -X POST 'https://api.gdc.cancer.gov/gene_expression/gene_selection' \
  -H 'Content-Type: application/json' \
  -d '{
    "case_ids": ["...","..."],
    "gene_ids": ["ENSG00000141510","ENSG00000181143"],
    "selection_size": 1
  }'
```

### Algorithm (from the spec)

1. For each (case, gene), compute `x = log2(uqfpkm + 1)`.
2. For each gene, compute the stddev of x-values. Genes with stddev=0 are ineligible.
3. For each gene, compute the median. Genes below `min_median_log2_uqfpkm` are ineligible.
4. Sort eligible genes by stddev descending.
5. Return the top `selection_size`.

### Response

A `gene_selection` key wrapping a list of genes, **already sorted by stddev descending** — each entry
carries the symbol and the two ranking quantities, not just the ID:

```json
{
  "gene_selection": [
    {"gene_id":"ENSG00000110484","symbol":"SCGB2A2","log2_uqfpkm_median":4.95,"log2_uqfpkm_stddev":4.00},
    {"gene_id":"ENSG00000124935","symbol":"SCGB1D2","log2_uqfpkm_median":4.01,"log2_uqfpkm_stddev":3.71}
  ]
}
```

(It is **not** a bare `[{"gene_id": …}]` array — index `resp["gene_selection"]`.) Take the `gene_id`s and
feed them into `/gene_expression/values` to build the matrix for those genes.

## Common workflows

1. **Heatmap of a curated gene list across a cohort:**
   `/gene_expression/values` with `gene_ids=[...]`, `cohort_id=...`, `tsv_units=median_centered_log2_uqfpkm`.

2. **Pick "interesting" genes for an exploratory analysis:**
   `/gene_expression/gene_selection` → take the returned gene_ids → feed them back into
   `/gene_expression/values` to get the matrix.

3. **Sanity-check a list of gene IDs:**
   `/gene_expression/availability` with `gene_ids=[...]` and no cases.
