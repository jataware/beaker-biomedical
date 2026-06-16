# Intended Behavior

The agent facets `files.access` for the project (e.g. TCGA-PAAD) and reports both buckets — open ≈4,971 and controlled ≈7,882 (total ≈12,853) — with the right interpretation: open files (clinical, derived expression, masked SSM) download with no token, while controlled files (BAMs and aligned reads under a dbGaP `acl`) need a token plus project authorization.

# Incorrect Behavior

The agent claims all GDC data is open (or all requires a token), or reports only the total file count without the open/controlled split.
