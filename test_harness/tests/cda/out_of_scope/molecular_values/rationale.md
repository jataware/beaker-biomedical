# Intended Behavior

CDA holds no expression or abundance values — only metadata locating where such data lives. The agent routes protein abundance to `proteomic-data-commons` and RNA expression to `genomic-data-commons`.

# Incorrect Behavior

The agent invents an `abundance` or `expression` column, or summarizes a value that does not exist in CDA.
