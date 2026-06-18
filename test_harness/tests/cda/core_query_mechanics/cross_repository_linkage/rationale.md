# Intended Behavior

The agent counts subjects present at BOTH repositories by intersecting them — `summarize_subjects(data_source=['IDC','GDC'])` in cdapython (a list to `data_source` means present at both), or the `subject_data_at_idc = true` / `subject_data_at_gdc = true` booleans in raw REST `MATCH_ALL`. Both approaches reach 15,699 subjects (verified 2026-06-18: cdapython list and REST booleans both return 15699), mapping IDC to imaging and GDC to genomic sequencing.

Note: the `*_data_at_*` booleans are NOT searchable in cdapython 2.1.0 (they raise "not a searchable CDA column"); they work only in raw REST. In cdapython the equivalent intersection is a list passed to `data_source`.

# Incorrect Behavior

The agent links repositories through the known-buggy `upstream_source` field, or falls back to a single keyword search instead of the `*_data_at_*` booleans.
