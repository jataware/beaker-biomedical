# scRNA-Seq Gene Expression endpoint

Single endpoint: `POST https://api.gdc.cancer.gov/scrna_seq/gene_expression`. Returns per-cell
expression values from harmonized scRNA-Seq HDF5 files.

## Auth

`X-Auth-Token` (header or cookie). The data this endpoint exposes is typically controlled-access —
a token from a user authorized for the associated `phs*` ACL is required.

## Request shape

Exactly one of `case_id` or `file_id` (mutually exclusive). 1–10 gene IDs per request.

```json
{ "case_id": "94f90e9a-ecfe-4682-8d19-2ac88b31a5b8",
  "gene_ids": ["ENSG00000139618"] }
```

```json
{ "file_id": "7b688f18-2802-4892-a0df-3be06ec76958",
  "gene_ids": ["ENSG00000139618", "ENSG00000141510"] }
```

Validation rules:

| Rule | Error |
|---|---|
| `gene_ids` length 1–10 | `gene_ids requires at least 1 item` / `gene_ids can only have at most only 10 items` |
| Exactly one of case/file id | `specify either case_id or file_id, not both` |
| `case_id`, `file_id`, `gene_ids[i]` must validate UUID / `ENSG\d{11}` formats | `must follow uuid format` / `must follow ENSEMBL format at index N` |
| Case must have exactly one scRNA-Seq HDF5 file | `does not have any associated gene expression files` / `has more than one associated gene expression file: [...]` |

## Response

```json
{
  "data": [
    {
      "case_id": "94f90e9a-ecfe-4682-8d19-2ac88b31a5b8",
      "file_id": "5b383196-0109-4452-8bce-459308d5b394",
      "gene_id": "ENSG00000139618",
      "cells": [
        { "cell_id": "AAACCCAAGCCACTCG-1", "expression": 0.693147 }
      ],
      "errors": []
    }
  ]
}
```

One element of `data` per (case/file, gene) pair. `cells` is the full barcode → normalized expression
mapping for that pair. When a gene has no data, `cells: []` plus an error in `errors`:

```json
"errors": [ { "message": "Data Error - cannot find data for gene ENSG00000123456" } ]
```

## Error responses

| HTTP | Cause |
|---|---|
| 400 | Validation failures (missing IDs, both IDs given, too many genes, bad formats, multiple HDF5 files associated with case) |
| 403 | User not authorized for the file's ACL |
| 404 | Case or file not found |
| 451 | File redacted for legal reasons |

## Notes

- The HDF5 normalization is GDC-internal. The `expression` value is a normalized log-scale value
  suitable for visualization, not raw UMI counts.
- For bulk RNA-Seq use `/gene_expression/values` instead (see [GENE-EXPRESSION.md](GENE-EXPRESSION.md)).
- For multi-case scRNA-Seq analyses, batch your calls per case (the endpoint is 1 case × ≤10 genes).
