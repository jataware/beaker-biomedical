# Intended Behavior

The agent wildcards the free-text diagnosis, discovering the variants with `column_values('diagnosis', filters='*melanoma*')` and then filtering `summarize_subjects(match_all=['diagnosis = *melanoma*'])` (cdapython expands `*`). The dominant term `Malignant melanoma` alone reaches ≈1,432 subjects; the full wildcard cohort is somewhat larger.

Verified live 2026-06-18: there is no bare `Melanoma` value — `column_values('diagnosis')` contains only ~12 melanoma variants (`Malignant melanoma` value_count 4,029, `Nevi and melanomas` 163, `Nodular melanoma` 41, `Epithelioid cell melanoma` 30, `Spindle cell melanoma` 27, `Amelanotic melanoma` 18, …). `diagnosis = melanoma` (exact) = 0 subjects. `diagnosis = Malignant melanoma` = 1,432 subjects; `diagnosis = *melanoma*` (full wildcard cohort) = 1,444 subjects. Both are within the 20% tolerance of the target 1,432.

# Incorrect Behavior

The agent filters the exact `melanoma` or `Melanoma` with no wildcard, which returns 0, and then reports zero or stops instead of using `*melanoma*`.
