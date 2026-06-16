# Intended Behavior

The agent recognizes nanotechnology as GC-only data and uses the real DOI-style key `10.17917` (not a `phs######`) on a caNanoLab node. `studies(study_acronyms: ["caNanoLab"])` confirms `phs_accession "10.17917"`, `study_data_types ["Nanotechnology"]`, and Open access; keyed by that accession the nodes return real counts — characterizations ≈1,456, compositions ≈1,657, publications ≈308, protocols ≈359, investigators 1 (PI Piotr Grodzinski).

# Incorrect Behavior

The agent assumes the key is a `phs######` accession (e.g. guessing `phs010017`, which returns an empty list with no error and reads as "no data"), reports no nanotech data, or tries to route nanotech to a specialized commons that does not exist.
