# Expect

- **Correct:** CDA does neither — it returns `drs_uri` + `access` only. Resolve bytes in a cloud
  workspace (ISB-CGC / Velsera CGC / Terra; controlled needs dbGaP); variant calling is a pipeline in
  that workspace or a GDC-served product. Locate with CDA, then hand off.

# Failure Cases

- **Fail signs:** writes a `cdapython` "download"/"slice" call; claims CDA runs pipelines.

# Automated Checks

```yaml
checks:
  - behavior: "declined to download/process bytes in CDA; routed bytes to a cloud workspace and variant calling to a pipeline/GDC product"
  - substring_any: ["drs_uri", "ISB-CGC", "CGC", "Terra", "cloud workspace", "dbGaP"]
  - must_not_contain: [".download(", "CDA runs the pipeline", "CDA calls variants", "slice the BAM in CDA"]
```
