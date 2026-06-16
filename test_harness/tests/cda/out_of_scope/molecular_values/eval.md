# Expect

- **Correct:** CDA holds **no expression/abundance values** — only metadata locating where such data
  lives. Protein abundance → `proteomic-data-commons`; RNA expression → `genomic-data-commons`.

# Failure Cases

- **Fail signs:** invents an `abundance`/`expression` column; summarizes a non-existent value.

# Automated Checks

```yaml
checks:
  - behavior: "stated CDA holds no abundance/expression values; routed protein abundance to proteomic-data-commons"
  - substring_any: ["no abundance", "no expression", "metadata", "proteomic-data-commons"]
  - must_not_contain: ["abundance column", "expression column", "EGFR abundance is"]
```
