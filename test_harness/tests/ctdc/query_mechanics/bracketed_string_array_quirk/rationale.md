# Intended Behavior

The agent pages past the default 10 rows to return all ~50 colorectal participants, and parses the bracketed-string fields into real lists. `targeted_therapy` for `MSB-01627` is the string `"[Cetuximab, Bevacizumab]"`, which a clean parse (strip the `[]`, split on `", "`) turns into `["Cetuximab", "Bevacizumab"]` (2 drugs) — not the literal string and not a single item. Multi-valued `anatomical_collection_site` and `tissue_category` behave the same way, the latter sometimes with an empty element (e.g. `"[Metastatic, , Primary]"`).

# Incorrect Behavior

The agent prints the raw `"[...]"` strings, treats a single-drug string as a character list, crashes trying to JSON-decode the bracketed string, or returns only 10 rows assuming that is the whole cohort.
