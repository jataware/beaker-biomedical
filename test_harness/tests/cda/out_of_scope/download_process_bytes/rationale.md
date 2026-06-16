# Intended Behavior

CDA neither moves nor processes bytes — it returns `drs_uri` and `access` only. The agent locates the files in CDA, then hands off: bytes are resolved in a cloud workspace (ISB-CGC, Velsera CGC, or Terra; controlled data needs dbGaP), and variant calling is a pipeline in that workspace or a GDC-served product.

# Incorrect Behavior

The agent writes a `cdapython` download or slice call, or claims CDA runs pipelines.
