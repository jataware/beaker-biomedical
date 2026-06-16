# Intended Behavior

The agent wildcards the free-text diagnosis, discovering the variants with `column_values('diagnosis', filters='*melanoma*')` and then filtering `summarize_subjects(match_all=['diagnosis = *melanoma*'])` (cdapython expands `*`). The dominant term `Malignant melanoma` alone reaches ≈1,432 subjects (≈1,229 of them at GDC); the full wildcard cohort is somewhat larger.

# Incorrect Behavior

The agent filters the exact `melanoma` or `Melanoma` with no wildcard, which returns 0, and then reports zero or stops instead of using `*melanoma*`.
